"""Unit tests for the /health endpoint (no database, no external I/O)."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_200_and_ok_body() -> None:
    """GET /health should return 200 with {"status": "ok"}."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
