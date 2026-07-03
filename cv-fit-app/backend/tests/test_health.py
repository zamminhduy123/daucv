"""Tests for health-check endpoint and route registration."""

from fastapi.testclient import TestClient


def test_health_returns_200(client: TestClient) -> None:
    """Health check is mounted at / (root), not /health."""
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "message" in data
