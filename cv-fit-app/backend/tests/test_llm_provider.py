"""Behavior tests for external LLM provider adapters."""

import asyncio
from typing import Any

from pydantic import BaseModel

from app.models.responses import CVAnalysisGenerationResponse
from app.prompts.system_prompts import (
    CV_ANALYSIS_CONTEXT_WITH_JD,
    build_cv_analysis_prompt,
)
from app.services import llm_provider
from app.services.llm_provider import QwenCustomProvider


class _StructuredResult(BaseModel):
    label: str
    scores: list[int]


def test_qwen_constrains_output_to_response_schema(
    monkeypatch,
) -> None:
    captured: dict[str, Any] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {
                "choices": [
                    {
                        "message": {
                            "content": '{"label":"match","scores":[90]}',
                        },
                    },
                ],
                "usage": {"prompt_tokens": 5, "completion_tokens": 7},
            }

    class FakeClient:
        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *_: object) -> None:
            return None

        async def post(self, _: str, **kwargs: Any) -> FakeResponse:
            captured.update(kwargs)
            return FakeResponse()

    monkeypatch.setattr(llm_provider.httpx, "AsyncClient", FakeClient)
    provider = QwenCustomProvider(
        name="Local-Qwen",
        model="qwen-test",
        api_key="secret",
        endpoint="http://qwen.test/v1/chat/completions",
        timeout=30,
        max_output_tokens=2048,
    )

    result = asyncio.run(
        provider.generate_structured(
            system_prompt="Return JSON.",
            user_content="Analyze this input.",
            response_model=_StructuredResult,
        ),
    )

    payload = captured["json"]
    assert result.data == _StructuredResult(label="match", scores=[90])
    assert payload["response_format"] == {
        "type": "json_object",
        "schema": _StructuredResult.model_json_schema(),
    }
    assert payload["chat_template_kwargs"] == {"enable_thinking": False}
    assert payload["max_tokens"] == 2048
    assert captured["headers"]["Connection"] == "close"


def test_qwen_timeout_has_actionable_error(monkeypatch) -> None:
    class FakeClient:
        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *_: object) -> None:
            return None

        async def post(self, _: str, **__: Any) -> None:
            raise llm_provider.httpx.ReadTimeout("read timed out")

    monkeypatch.setattr(llm_provider.httpx, "AsyncClient", FakeClient)
    provider = QwenCustomProvider(
        name="Remote-Qwen",
        model="qwen-test",
        api_key="secret",
        endpoint="http://qwen.test/v1/chat/completions",
        timeout=600,
    )

    try:
        asyncio.run(
            provider.generate_structured(
                system_prompt="Return JSON.",
                user_content="Analyze this input.",
                response_model=_StructuredResult,
            )
        )
    except TimeoutError as exc:
        assert str(exc) == "Remote Qwen timed out after 600s"
    else:
        raise AssertionError("Expected Qwen timeout")


def test_cv_generation_contract_omits_backend_derived_documents() -> None:
    schema = CVAnalysisGenerationResponse.model_json_schema()
    prompt = build_cv_analysis_prompt(CV_ANALYSIS_CONTEXT_WITH_JD, "en")

    assert "tailored_cv" not in schema["properties"]
    assert "document_v2" not in schema["properties"]
    assert "source_document_v2" not in schema["properties"]
    assert "- tailored_cv:" not in prompt
    assert "ats_readiness" in schema["properties"]
    assert "ats_readiness" in schema["required"]


def test_openai_provider_passes_extra_body(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    class FakeChoice:
        message = type("Message", (), {"content": '{"label":"ok","scores":[100]}'})()

    class FakeCompletion:
        def __init__(self) -> None:
            self.choices = [FakeChoice()]
            self.usage = type(
                "Usage", (), {"prompt_tokens": 10, "completion_tokens": 20}
            )()

    class FakeCompletions:
        async def create(self, **kwargs: Any) -> FakeCompletion:
            captured.update(kwargs)
            return FakeCompletion()

    class FakeChat:
        completions = FakeCompletions()

    class FakeAsyncOpenAI:
        def __init__(self, api_key: str, base_url: str, max_retries: int = 1) -> None:
            self.api_key = api_key
            self.base_url = base_url
            self.chat = FakeChat()

    monkeypatch.setattr(llm_provider, "AsyncOpenAI", FakeAsyncOpenAI)

    provider = llm_provider.OpenAIProvider(
        name="NVIDIA",
        model="nvidia/nemotron-3-nano-30b-a3b",
        api_key="nv-secret",
        base_url="https://integrate.api.nvidia.com/v1",
        extra_body={"reasoning_budget": 16384},
        timeout=30.0,
        max_output_tokens=16384,
    )

    result = asyncio.run(
        provider.generate_structured(
            system_prompt="Return JSON.",
            user_content="Hello",
            response_model=_StructuredResult,
        ),
    )

    assert result.data == _StructuredResult(label="ok", scores=[100])
    assert captured["extra_body"] == {"reasoning_budget": 16384}
    assert captured["model"] == "nvidia/nemotron-3-nano-30b-a3b"
    assert captured["max_tokens"] == 16384


def test_provider_waterfall_order() -> None:
    from app.core import config

    assert len(config.PROVIDERS) >= 2
    assert config.PROVIDERS[0].name == "NVIDIA"
    assert config.PROVIDERS[1].name == "Gemini"
