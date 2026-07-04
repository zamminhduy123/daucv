"""
LLM Provider implementations with a consistent interface.

Each provider implements ``generate_structured`` which returns a ``ProviderResult``
containing the parsed Pydantic model and usage metrics (tokens).
"""

import re
from abc import ABC, abstractmethod
from typing import Any, TypeVar

import httpx
from google import genai
from openai import AsyncOpenAI
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class ProviderResult(BaseModel):
    """Container for LLM response and metadata."""

    data: Any
    input_tokens: int = 0
    output_tokens: int = 0
    raw_response: str = ""


class BaseAIProvider(ABC):
    def __init__(self, name: str, model: str):
        self.name = name
        self.model = model

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
    """
    Standard provider for any OpenAI-compatible API (Gemini-OpenAI, Groq, OpenRouter, vLLM).
    """

    def __init__(self, name: str, model: str, api_key: str, base_url: str):
        super().__init__(name, model)
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

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

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=temperature,
        )

        content = response.choices[0].message.content or "{}"
        parsed = response_model.model_validate_json(content)

        input_tokens = 0
        output_tokens = 0
        if response.usage:
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens

        return ProviderResult(
            data=parsed,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            raw_response=content,
        )


class GeminiNativeProvider(BaseAIProvider):
    """
    Uses Google's native Generative AI SDK (google-genai).
    """

    def __init__(self, name: str, model: str, api_key: str):
        super().__init__(name, model)
        self.client = genai.Client(api_key=api_key)

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
    """
    Direct HTTP implementation for Ollama local servers.
    """

    def __init__(self, name: str, model: str, endpoint: str):
        super().__init__(name, model)
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
                    [f"{m.get('role')}: {m.get('content')}" for m in user_content]
                )
            else:
                content_str = user_content

            prompt = f"{system_prompt}\n\nInput:\n{content_str}"

            res = await http_client.post(
                self.endpoint,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "format": response_model.model_json_schema(),
                    "stream": False,
                    "options": {"temperature": temperature},
                },
                timeout=300.0,
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
    """
    Custom provider for Qwen or local endpoints with specific JSON extraction needs.
    """

    def __init__(self, name: str, model: str, api_key: str, endpoint: str):
        super().__init__(name, model)
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

            res = await http_client.post(
                self.endpoint,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "response_format": {"type": "json_object"},
                },
                timeout=300.0,
            )
            res.raise_for_status()
            data = res.json()
            content = data["choices"][0]["message"]["content"]

            # Extraction helper
            json_str = content
            json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
            if json_match:
                json_str = json_match.group(1)

            parsed = response_model.model_validate_json(json_str)

            usage = data.get("usage", {})
            return ProviderResult(
                data=parsed,
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
                raw_response=content,
            )
