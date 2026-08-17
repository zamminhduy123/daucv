"""Shared fixtures for backend tests."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

# Lazy imports — only load the full FastAPI app when tests actually need
# the ``client`` fixture.  Pure unit tests (e.g. Phase 0 extraction tests)
# should not trigger these imports to avoid pulling in database drivers.
try:
    from fastapi.testclient import TestClient

    from app.core.db import Database
    from app.dependencies import get_current_user
    from app.main import create_app

    _APP_LOADED = True
except ImportError:  # pragma: no cover
    # Only skip for missing optional dependencies (e.g. asyncpg, jwt).
    # Syntax errors, circular imports, and configuration failures must
    # surface as test failures so they are not silently swallowed.
    _APP_LOADED = False

MOCK_USER = {
    "id": "12345678-1234-1234-1234-123456789012",
    "email": "test@example.com",
    "name": "Test User",
    "image": None,
    "credits": 10,
}


@pytest.fixture
def client():
    """Provide a TestClient for the FastAPI app with mocked auth and database."""
    if not _APP_LOADED:  # pragma: no cover
        pytest.skip("FastAPI app not available (missing dependencies).")
    app = create_app()

    async def mock_get_current_user():
        return MOCK_USER

    # Override the JWT auth check
    app.dependency_overrides[get_current_user] = mock_get_current_user

    # Mock Database direct methods
    async def mock_fetch_one(*args, **kwargs):
        if "user_cvs" in args[0] and "is_active = TRUE" in args[0]:
            return {
                "id": "12345678-1234-1234-1234-123456789012",
                "cv_filename": "test.pdf",
                "cv_text": "Sample CV Text",
                "is_active": True,
                "created_at": datetime.now(),
            }
        return None

    async def mock_fetch_all(*args, **kwargs):
        return [
            {
                "id": "12345678-1234-1234-1234-123456789012",
                "cv_filename": "test.pdf",
                "cv_text": "Sample CV Text",
                "is_active": True,
                "created_at": datetime.now(),
            },
        ]

    async def mock_execute(*args, **kwargs):
        return "UPDATE 1"

    # Setup the mock asyncpg pool/connection structure
    mock_conn = AsyncMock()
    mock_conn.fetchrow.return_value = {
        "id": "12345678-1234-1234-1234-123456789012",
        "cv_filename": "test.pdf",
        "cv_text": "Sample CV Text",
        "is_active": True,
        "created_at": datetime.now(),
    }
    mock_conn.execute = AsyncMock(return_value="UPDATE 1")
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

    # Save the original pool to restore later
    original_pool = Database.pool
    Database.pool = MockPool()

    # Mock database connections and credit deductions
    with (
        patch(
            "app.api.routes.user.reserve_credits",
            new_callable=AsyncMock,
        ),
        patch(
            "app.api.routes.user.refund_credits",
            new_callable=AsyncMock,
        ),
        patch(
            "app.api.routes.jobs.reserve_credits",
            new_callable=AsyncMock,
        ),
        patch(
            "app.api.routes.jobs.refund_credits",
            new_callable=AsyncMock,
        ),
        patch(
            "app.api.routes.billing.add_credits",
            new_callable=AsyncMock,
        ) as mock_add,
        patch(
            "app.core.db.Database.connect",
            new_callable=AsyncMock,
        ) as mock_connect,
        patch(
            "app.core.db.Database.disconnect",
            new_callable=AsyncMock,
        ) as mock_disconnect,
        patch(
            "app.core.db.Database.fetch_one",
            side_effect=mock_fetch_one,
        ),
        patch(
            "app.core.db.Database.fetch_all",
            side_effect=mock_fetch_all,
        ),
        patch(
            "app.core.db.Database.execute",
            side_effect=mock_execute,
        ),
        TestClient(app) as c,
    ):
        yield c

    # Cleanups
    Database.pool = original_pool
    app.dependency_overrides.clear()
