from unittest.mock import AsyncMock, patch

import pytest

from scripts.daily_top_up import run_daily_top_up


@pytest.mark.asyncio
async def test_run_daily_top_up_no_users():
    # Mock database connection and methods
    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = []  # No users returned

    mock_conn.execute = AsyncMock()
    mock_conn.transaction = lambda: MockTransaction()

    class MockTransaction:
        async def __aenter__(self):
            return mock_conn

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    class MockConnection:
        async def __aenter__(self):
            return mock_conn

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        def transaction(self):
            return MockTransaction()

    class MockPool:
        def acquire(self):
            return MockConnection()

    with (
        patch("app.core.db.Database.pool", new=MockPool()),
        patch("app.core.db.Database.connect", new_callable=AsyncMock),
        patch("app.core.db.Database.disconnect", new_callable=AsyncMock),
    ):
        count = await run_daily_top_up()
        assert count == 0
        mock_conn.execute.assert_not_called()


@pytest.mark.asyncio
async def test_run_daily_top_up_with_users():
    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = [{"id": "user-1-uuid"}, {"id": "user-2-uuid"}]
    mock_conn.execute = AsyncMock()
    mock_conn.transaction = lambda: MockTransaction()

    class MockTransaction:
        async def __aenter__(self):
            return mock_conn

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    class MockConnection:
        async def __aenter__(self):
            return mock_conn

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        def transaction(self):
            return MockTransaction()

    class MockPool:
        def acquire(self):
            return MockConnection()

    with (
        patch("app.core.db.Database.pool", new=MockPool()),
        patch("app.core.db.Database.connect", new_callable=AsyncMock),
        patch("app.core.db.Database.disconnect", new_callable=AsyncMock),
    ):
        count = await run_daily_top_up()
        assert count == 2
        assert mock_conn.execute.call_count == 2

        # Verify first call is UPDATE
        first_call_args = mock_conn.execute.call_args_list[0][0]
        assert "UPDATE public.users SET credits = credits + 5" in first_call_args[0]

        # Verify second call is INSERT into credit_transactions
        second_call_args = mock_conn.execute.call_args_list[1][0]
        assert "INSERT INTO public.credit_transactions" in second_call_args[0]
