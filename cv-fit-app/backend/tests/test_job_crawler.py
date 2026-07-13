"""Regression tests for the production job-search orchestration."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest

from app.services import job_crawler, search_engine


@pytest.mark.asyncio
async def test_search_jobs_falls_back_when_browser_cannot_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A Render Chromium failure must not turn the whole API request into a 500."""

    @asynccontextmanager
    async def broken_browser() -> AsyncIterator[None]:
        raise RuntimeError("chromium failed to start")
        yield  # pragma: no cover - required to make this an async generator

    fallback_job = {
        "id": "itviec-se-1",
        "source": "itviec",
        "title": "Backend Engineer",
        "company": "Example Co",
        "location": "Ho Chi Minh City",
        "salary": None,
        "level": None,
        "skills": ["Python"],
        "posted_text": None,
        "url": "https://itviec.com/it-jobs/backend-engineer-1",
        "description_snippet": None,
    }
    fallback = AsyncMock(return_value=[fallback_job])
    monkeypatch.setattr(job_crawler, "managed_browser", broken_browser)
    monkeypatch.setattr(search_engine, "search_via_engine_for_source", fallback)

    result = await job_crawler.search_jobs(
        cv_text="Python backend engineer",
        target_roles=["Backend Engineer"],
        skills=["Python"],
        seniority="mid",
        location="Ho Chi Minh City",
        years_of_experience=3,
        queries=["Backend Engineer"],
        enabled_sources=["itviec"],
    )

    assert result["total"] == 1
    assert result["jobs"][0]["url"] == fallback_job["url"]
    assert result["sourceStatus"] == [
        {"source": "itviec", "status": "success", "count": 1, "error": None}
    ]
    fallback.assert_awaited_once()


@pytest.mark.asyncio
async def test_managed_browser_cleans_up_partial_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    browser_manager = AsyncMock()
    browser_manager.start.side_effect = RuntimeError("chromium failed to start")
    monkeypatch.setattr(job_crawler, "_browser_mgr", browser_manager)

    with pytest.raises(RuntimeError, match="chromium failed to start"):
        async with job_crawler.managed_browser():
            pytest.fail("a failed browser must not yield a manager")

    browser_manager.stop.assert_awaited_once()
