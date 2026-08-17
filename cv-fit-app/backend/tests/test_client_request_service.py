import asyncio

import pytest

from app.services.client_request_service import (
    ClientDisconnectedError,
    await_while_client_connected,
)


def test_disconnect_cancels_inflight_work() -> None:
    cancelled = False

    class DisconnectedRequest:
        async def is_disconnected(self) -> bool:
            return True

    async def long_running_work() -> None:
        nonlocal cancelled
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            cancelled = True
            raise

    with pytest.raises(ClientDisconnectedError):
        asyncio.run(
            await_while_client_connected(
                DisconnectedRequest(),
                long_running_work(),
                poll_interval=0.001,
            )
        )

    assert cancelled
