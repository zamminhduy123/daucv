"""LLM Provider implementations with a consistent interface.

Each provider implements ``generate_structured`` which returns a ``ProviderResult``
containing the parsed Pydantic model and usage metrics (tokens).
"""

import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Any, TypeVar

import httpx
from google import genai
from openai import AsyncOpenAI
from pydantic import BaseModel

_logger = logging.getLogger("app.services.llm_provider")

T = TypeVar("T", bound=BaseModel)


class ProviderResult(BaseModel):
    """Container for LLM response and metadata."""

    data: Any
    input_tokens: int = 0
    output_tokens: int = 0
    raw_response: str = ""


def _extract_json_string(content: str) -> str:
    content_str = content.strip()
    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content_str)
    if json_match:
        content_str = json_match.group(1).strip()
    else:
        first_brace = content_str.find("{")
        last_brace = content_str.rfind("}")
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            content_str = content_str[first_brace : last_brace + 1]

    if content_str.startswith("{"):
        try:
            data = json.loads(content_str)
            if isinstance(data, dict):
                for key in ("./output.json", "output.json", "output"):
                    if (
                        key in data
                        and isinstance(data[key], str)
                        and data[key].strip().startswith("{")
                    ):
                        return data[key].strip()
        except Exception:
            pass

    return content_str


class BaseAIProvider(ABC):
    def __init__(
        self,
        name: str,
        model: str,
        timeout: float | None = None,
        max_output_tokens: int | None = None,
    ):
        self.name = name
        self.model = model
        self.timeout = timeout
        self.max_output_tokens = max_output_tokens

    @property
    def is_configured(self) -> bool:
        return True

    @abstractmethod
    async def generate_structured(
        self,
        system_prompt: str,
        user_content: Any,
        response_model: type[T],
        temperature: float = 0.7,
    ) -> ProviderResult:
        pass


class OpenAIProvider(BaseAIProvider):
    """Standard provider for any OpenAI-compatible API (Gemini-OpenAI, Groq, OpenRouter, vLLM, NVIDIA)."""

    def __init__(
        self,
        name: str,
        model: str,
        api_key: str,
        base_url: str,
        timeout: float | None = None,
        max_output_tokens: int | None = None,
        extra_body: dict[str, Any] | None = None,
    ):
        super().__init__(name, model, timeout, max_output_tokens)
        self.api_key = api_key
        self.base_url = base_url
        self.client = AsyncOpenAI(
            api_key=api_key or "not-needed",
            base_url=base_url,
            max_retries=0,
        )
        self.extra_body = extra_body

    @property
    def is_configured(self) -> bool:
        if (
            "127.0.0.1" in self.base_url
            or "localhost" in self.base_url
            or "0.0.0.0" in self.base_url
        ):
            return True
        return bool(self.api_key and self.api_key.strip())

    async def generate_structured(
        self,
        system_prompt: str,
        user_content: Any,
        response_model: type[T],
        temperature: float = 0.7,
    ) -> ProviderResult:
        messages = [{"role": "system", "content": system_prompt}]
        if isinstance(user_content, list):
            messages.extend(user_content)
        else:
            messages.append({"role": "user", "content": user_content})

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": temperature,
            "timeout": self.timeout,
            "max_tokens": self.max_output_tokens,
        }
        if self.extra_body:
            kwargs["extra_body"] = self.extra_body

        _logger.info(
            "Sending request to provider %s (model: %s)", self.name, self.model
        )
        response = await self.client.chat.completions.create(**kwargs)

        choice = response.choices[0]
        finish_reason = getattr(choice, "finish_reason", "unknown")
        raw_msg = choice.message
        content = (
            raw_msg.content
            or getattr(raw_msg, "reasoning_content", None)
            or getattr(raw_msg, "reasoning", None)
            or ""
        )
        if not content.strip():
            raise ValueError(f"Provider {self.name} returned empty content.")

        json_str = _extract_json_string(content)

        _logger.info(
            "Provider %s responded. finish_reason=%s, raw_len=%d, extracted_len=%d",
            self.name,
            finish_reason,
            len(content),
            len(json_str),
        )

        try:
            parsed = response_model.model_validate_json(json_str)
        except Exception as err:
            _logger.error(
                "Provider %s JSON validation error: %s | finish_reason: %s | Extracted snippet: %r | Raw snippet: %r",
                self.name,
                err,
                finish_reason,
                json_str[:300],
                content[:300],
            )
            raise

        input_tokens = 0
        output_tokens = 0
        if response.usage:
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens

            _logger.info(
                "Tokens used by %s: Input: %d, Output: %d",
                self.name,
                input_tokens,
                output_tokens,
            )

        return ProviderResult(
            data=parsed,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            raw_response=content,
        )


class GeminiNativeProvider(BaseAIProvider):
    """Uses Google's native Generative AI SDK (google-genai)."""

    def __init__(
        self,
        name: str,
        model: str,
        api_key: str,
        timeout: float | None = None,
    ):
        super().__init__(name, model, timeout)
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key or "not-needed")

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    async def generate_structured(
        self,
        system_prompt: str,
        user_content: Any,
        response_model: type[T],
        temperature: float = 0.7,
    ) -> ProviderResult:
        config = {
            "system_instruction": system_prompt,
            "temperature": temperature,
            "response_mime_type": "application/json",
            "response_schema": response_model,
        }

        # Note: native SDK is synchronous in current version, but we wrap it
        completion = self.client.models.generate_content(
            model=self.model,
            contents=user_content,
            config=config,
        )

        parsed = completion.parsed
        if parsed is None:
            raw = completion.text or "{}"
            parsed = response_model.model_validate_json(raw)

        # TODO: Extract token usage from native SDK response if available
        return ProviderResult(
            data=parsed,
            raw_response=completion.text or "",
        )


class OllamaProvider(BaseAIProvider):
    """Direct HTTP implementation for Ollama local servers."""

    def __init__(
        self,
        name: str,
        model: str,
        endpoint: str,
        timeout: float | None = None,
    ):
        super().__init__(name, model, timeout)
        self.endpoint = endpoint

    async def generate_structured(
        self,
        system_prompt: str,
        user_content: Any,
        response_model: type[T],
        temperature: float = 0.7,
    ) -> ProviderResult:
        async with httpx.AsyncClient() as http_client:
            if isinstance(user_content, list):
                content_str = "\n".join(
                    [f"{m.get('role')}: {m.get('content')}" for m in user_content],
                )
            else:
                content_str = user_content

            prompt = f"{system_prompt}\n\nInput:\n{content_str}"

            timeout_val = self.timeout if self.timeout is not None else 300.0
            res = await http_client.post(
                self.endpoint,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "format": response_model.model_json_schema(),
                    "stream": False,
                    "options": {"temperature": temperature},
                },
                timeout=timeout_val,
            )
            res.raise_for_status()
            data = res.json()
            content = data.get("response", "{}")
            parsed = response_model.model_validate_json(content)

            return ProviderResult(
                data=parsed,
                input_tokens=data.get("prompt_eval_count", 0),
                output_tokens=data.get("eval_count", 0),
                raw_response=content,
            )


class QwenCustomProvider(BaseAIProvider):
    """Custom provider for Qwen or local endpoints with specific JSON extraction needs."""

    def __init__(
        self,
        name: str,
        model: str,
        api_key: str,
        endpoint: str,
        timeout: float | None = None,
        max_output_tokens: int | None = None,
    ):
        super().__init__(name, model, timeout, max_output_tokens)
        self.api_key = api_key
        self.endpoint = endpoint

    async def generate_structured(
        self,
        system_prompt: str,
        user_content: Any,
        response_model: type[T],
        temperature: float = 0.7,
    ) -> ProviderResult:
        async with httpx.AsyncClient() as http_client:
            messages = [{"role": "system", "content": system_prompt}]
            if isinstance(user_content, list):
                messages.extend(user_content)
            else:
                messages.append({"role": "user", "content": user_content})

            _logger.info(
                "Sending request to provider %s (model: %s)", self.name, self.model
            )

            timeout_val = self.timeout if self.timeout is not None else 300.0
            try:
                res = await http_client.post(
                    self.endpoint,
                    # llama-server can leave a keep-alive response open after
                    # finishing a large non-streaming JSON generation. Closing
                    # this request's connection forces a complete response
                    # boundary without affecting the next queued request.
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Connection": "close",
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": temperature,
                        "response_format": {
                            "type": "json_object",
                            "schema": response_model.model_json_schema(),
                        },
                        "chat_template_kwargs": {"enable_thinking": False},
                        "max_tokens": self.max_output_tokens,
                    },
                    timeout=timeout_val,
                )
            except httpx.TimeoutException as exc:
                raise TimeoutError(
                    f"Remote Qwen timed out after {timeout_val:g}s"
                ) from exc
            res.raise_for_status()
            data = res.json()
            choice = data["choices"][0]
            msg = choice["message"]
            finish_reason = choice.get("finish_reason", "unknown")
            content = msg.get("content") or msg.get("reasoning_content") or "{}"

            json_str = _extract_json_string(content)

            _logger.info(
                "Provider %s responded. finish_reason=%s, raw_len=%d, extracted_len=%d",
                self.name,
                finish_reason,
                len(content),
                len(json_str),
            )

            try:
                parsed = response_model.model_validate_json(json_str)
            except Exception as err:
                _logger.error(
                    "Provider %s JSON validation error: %s | finish_reason: %s | Extracted snippet: %r | Raw snippet: %r",
                    self.name,
                    err,
                    finish_reason,
                    json_str[:300],
                    content[:300],
                )
                raise

            usage = data.get("usage", {})
            return ProviderResult(
                data=parsed,
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
                raw_response=content,
            )
