"""Contract tests for the streamed CV-analysis route."""

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any, cast
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

ProgressReporter = Callable[
    [str, str, dict[str, Any] | None],
    Awaitable[None],
]


def test_analyze_cv_stream_reports_progress_then_timeout_and_refunds(
    client: TestClient,
) -> None:
    async def slow_analysis(**kwargs: object) -> None:
        progress = cast(ProgressReporter, kwargs["progress"])
        await progress("analyzing", "Đang phân tích...", None)
        await asyncio.sleep(1)

    with (
        patch(
            "app.api.routes.user.CV_ANALYSIS_REQUEST_TIMEOUT",
            0.01,
        ),
        patch(
            "app.api.routes.user.cv_analysis_service.analyze_cv",
            side_effect=slow_analysis,
        ),
        patch(
            "app.api.routes.user._refund_reserved_credit",
            new_callable=AsyncMock,
        ) as refund,
    ):
        response = client.post(
            "/api/analyze-cv/stream",
            json={"cv_text": "Backend engineer", "jd_text": "Backend role"},
        )

    assert response.status_code == 200
    events = [json.loads(line) for line in response.text.splitlines()]
    assert [event["type"] for event in events] == [
        "progress",
        "progress",
        "error",
    ]
    assert events[1]["stage"] == "analyzing"
    assert events[-1]["status"] == 504
    refund.assert_awaited_once()
