"""Cancellation bridge between disconnected HTTP clients and long AI work."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from contextlib import suppress
from typing import Protocol, TypeVar


class DisconnectAwareRequest(Protocol):
    async def is_disconnected(self) -> bool: ...


class ClientDisconnectedError(Exception):
    """Raised after cancelling work whose HTTP client went away."""


T = TypeVar("T")


async def await_while_client_connected(
    request: DisconnectAwareRequest,
    work: Awaitable[T],
    *,
    poll_interval: float = 0.25,
) -> T:
    """Cancel ``work`` promptly when the requester aborts the HTTP request."""
    task = asyncio.ensure_future(work)
    try:
        while True:
            done, _ = await asyncio.wait({task}, timeout=poll_interval)
            if task in done:
                return task.result()
            if await request.is_disconnected():
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
                raise ClientDisconnectedError("Client disconnected; request cancelled.")
    finally:
        if not task.done():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
