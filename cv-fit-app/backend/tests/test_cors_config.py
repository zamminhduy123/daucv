"""CORS configuration regressions for local frontend development."""

from app.core.config import CORS_ALLOWED_ORIGINS


def test_cors_allows_nextjs_fallback_dev_port() -> None:
    assert "http://localhost:3001" in CORS_ALLOWED_ORIGINS
    assert "http://127.0.0.1:3001" in CORS_ALLOWED_ORIGINS
