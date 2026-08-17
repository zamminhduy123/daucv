"""Progress-event tests for the shared LLM provider waterfall."""

import asyncio
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from pydantic import BaseModel

from app.services import ai_service


class _StructuredResult(BaseModel):
    label: str
    scores: list[int]


def test_provider_waterfall_reports_retry_before_fallback(monkeypatch) -> None:
    retries: list[tuple[int, int]] = []

    class FailingProvider:
        name = "first"
        model = "first-model"

        async def generate_structured(self, **_: Any) -> None:
            raise RuntimeError("provider unavailable")

    class SuccessfulProvider:
        name = "second"
        model = "second-model"

        async def generate_structured(self, **_: Any) -> SimpleNamespace:
            return SimpleNamespace(
                data=_StructuredResult(label="ok", scores=[100]),
                input_tokens=1,
                output_tokens=1,
            )

    async def on_retry(attempt: int, total: int) -> None:
        retries.append((attempt, total))

    monkeypatch.setattr(
        ai_service.config,
        "PROVIDERS",
        [FailingProvider(), SuccessfulProvider()],
    )
    monkeypatch.setattr(ai_service, "log_llm_request", lambda _: None)
    monkeypatch.setattr(ai_service.asyncio, "sleep", AsyncMock())

    result = asyncio.run(
        ai_service.call_llm_with_fallback(
            "Return JSON.",
            "Analyze this.",
            _StructuredResult,
            on_retry=on_retry,
        ),
    )

    assert result == _StructuredResult(label="ok", scores=[100])
    assert retries == [(2, 2)]


def test_provider_waterfall_uses_feature_output_budget_without_mutating_provider(
    monkeypatch,
) -> None:
    observed_budgets: list[int] = []

    class SuccessfulProvider:
        name = "bounded"
        model = "bounded-model"
        max_output_tokens = 8192

        async def generate_structured(self, **_: Any) -> SimpleNamespace:
            observed_budgets.append(self.max_output_tokens)
            return SimpleNamespace(
                data=_StructuredResult(label="ok", scores=[100]),
                input_tokens=1,
                output_tokens=1,
            )

    provider = SuccessfulProvider()
    monkeypatch.setattr(ai_service.config, "PROVIDERS", [provider])
    monkeypatch.setattr(ai_service, "log_llm_request", lambda _: None)

    result = asyncio.run(
        ai_service.call_llm_with_fallback(
            "Return JSON.",
            "Analyze this.",
            _StructuredResult,
            max_output_tokens=2048,
        ),
    )

    assert result == _StructuredResult(label="ok", scores=[100])
    assert observed_budgets == [2048]
    assert provider.max_output_tokens == 8192


def test_remote_qwen_requests_are_serialized(monkeypatch) -> None:
    active = 0
    peak_active = 0

    class RemoteQwenProvider:
        name = "Remote-Qwen"
        model = "qwen-test"
        max_output_tokens = 8192

        async def generate_structured(self, **_: Any) -> SimpleNamespace:
            nonlocal active, peak_active
            active += 1
            peak_active = max(peak_active, active)
            await asyncio.sleep(0)
            active -= 1
            return SimpleNamespace(
                data=_StructuredResult(label="ok", scores=[100]),
                input_tokens=1,
                output_tokens=1,
            )

    monkeypatch.setattr(ai_service.config, "PROVIDERS", [RemoteQwenProvider()])
    monkeypatch.setattr(ai_service.config, "REMOTE_QWEN_MAX_CONCURRENT", 1)
    monkeypatch.setattr(ai_service, "_remote_qwen_semaphore", None)
    monkeypatch.setattr(ai_service, "log_llm_request", lambda _: None)

    async def run_two() -> None:
        await asyncio.gather(
            ai_service.call_llm_with_fallback(
                "Return JSON.", "first", _StructuredResult
            ),
            ai_service.call_llm_with_fallback(
                "Return JSON.", "second", _StructuredResult
            ),
        )

    asyncio.run(run_two())
    assert peak_active == 1


def test_remote_qwen_queue_has_a_deadline(monkeypatch) -> None:
    class RemoteQwenProvider:
        name = "Remote-Qwen"
        model = "qwen-test"
        max_output_tokens = 8192

        async def generate_structured(self, **_: Any) -> SimpleNamespace:
            raise AssertionError("A queued request must not acquire the busy slot")

    monkeypatch.setattr(ai_service.config, "PROVIDERS", [RemoteQwenProvider()])
    monkeypatch.setattr(
        ai_service.config,
        "REMOTE_QWEN_QUEUE_TIMEOUT",
        0.01,
        raising=False,
    )
    monkeypatch.setattr(ai_service, "_remote_qwen_semaphore", asyncio.Semaphore(0))
    monkeypatch.setattr(ai_service, "log_llm_request", lambda _: None)

    with pytest.raises(HTTPException, match="queue wait timed out"):
        asyncio.run(
            asyncio.wait_for(
                ai_service.call_llm_with_fallback(
                    "Return JSON.",
                    "queued request",
                    _StructuredResult,
                ),
                timeout=0.1,
            )
        )
