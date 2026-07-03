"""Shared fixtures for backend tests."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture()
def client():
    """Provide a TestClient for the FastAPI app."""
    app = create_app()
    with TestClient(app) as c:
        yield c
