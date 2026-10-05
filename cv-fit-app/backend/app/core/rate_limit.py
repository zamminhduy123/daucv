"""Lightweight per-user sliding-window rate limiter (FastAPI dependency).

IMPORTANT: state is kept in this process's memory. Every uvicorn worker /
container instance has its own counters, so with N processes a user can make
up to N x the configured limit, and counters reset on restart. This is a
cost/abuse brake for expensive endpoints (LLM calls, PDF rendering), not a
global quota. Move the store to Redis if strict cross-process limits are needed.

Limits are configured in ``app.core.config`` (``RATE_LIMIT_*`` env vars).
"""

from __future__ import annotations

import math
import threading
import time
from collections import deque
from collections.abc import Callable

from fastapi import Depends, FastAPI, HTTPException, Request

from app.core import config
from app.dependencies import get_current_user

_PRUNE_EVERY = 1024


class SlidingWindowRateLimiter:
    """Counts hits per (group, key) inside a rolling time window.

    ``hit`` never awaits, so it is atomic with respect to the asyncio event
    loop; the ``threading.Lock`` additionally makes it safe if it is ever
    called from FastAPI's threadpool. The lock is never held across an await.
    """

    def __init__(
        self,
        window_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self._window = float(window_seconds)
        self._clock = clock
        self._hits: dict[tuple[str, str], deque[float]] = {}
        self._lock = threading.Lock()
        self._calls = 0

    def hit(self, group: str, key: str, limit: int) -> float | None:
        """Record one request.

        Returns ``None`` when allowed, otherwise the number of seconds until
        the oldest hit leaves the window (the request is NOT recorded).
        """
        with self._lock:
            now = self._clock()
            cutoff = now - self._window
            bucket = self._hits.setdefault((group, key), deque())
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                return max(bucket[0] + self._window - now, 0.0)
            bucket.append(now)
            self._calls += 1
            if self._calls % _PRUNE_EVERY == 0:
                self._prune(cutoff)
            return None

    def _prune(self, cutoff: float) -> None:
        stale = [k for k, b in self._hits.items() if not b or b[-1] <= cutoff]
        for k in stale:
            del self._hits[k]

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


_app_lock = threading.Lock()


def get_rate_limiter(app: FastAPI) -> SlidingWindowRateLimiter:
    """Return the limiter stored on ``app.state`` (created lazily, one per app)."""
    limiter = getattr(app.state, "rate_limiter", None)
    if limiter is None:
        with _app_lock:
            limiter = getattr(app.state, "rate_limiter", None)
            if limiter is None:
                limiter = SlidingWindowRateLimiter(config.RATE_LIMIT_WINDOW_SECONDS)
                app.state.rate_limiter = limiter
    return limiter


def rate_limit(group: str):
    """Build a dependency limiting the authenticated user within ``group``.

    Use as ``dependencies=[Depends(rate_limit("llm"))]`` on the route so the
    endpoint signature stays unchanged.
    """
    if group not in config.RATE_LIMITS_PER_WINDOW:
        raise ValueError(f"Unknown rate-limit group: {group}")

    async def _enforce(
        request: Request, user: dict = Depends(get_current_user)
    ) -> None:
        if not config.RATE_LIMIT_ENABLED:
            return
        limit = config.RATE_LIMITS_PER_WINDOW[group]
        retry_after = get_rate_limiter(request.app).hit(group, str(user["id"]), limit)
        if retry_after is not None:
            seconds = max(1, math.ceil(retry_after))
            raise HTTPException(
                status_code=429,
                detail=(
                    "Bạn đang gửi quá nhiều yêu cầu. "
                    f"Vui lòng thử lại sau {seconds} giây."
                ),
                headers={"Retry-After": str(seconds)},
            )

    _enforce.__name__ = f"rate_limit_{group}"
    return _enforce
