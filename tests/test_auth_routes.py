"""Route tests for POST /auth/login (mocked auth_service)."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.errors import AuthError
from app.main import app

client = TestClient(app)


def test_login_with_valid_credentials_returns_token() -> None:
    with patch("app.api.routes.auth.auth_service.authenticate", return_value="a.b.c") as mock_auth:
        resp = client.post("/auth/login", json={"username": "alice", "password": "correct-password"})

    assert resp.status_code == 200
    assert resp.json() == {"access_token": "a.b.c", "token_type": "bearer"}
    mock_auth.assert_called_once_with("alice", "correct-password")


def test_login_with_bad_password_returns_generic_401() -> None:
    with patch("app.api.routes.auth.auth_service.authenticate", side_effect=AuthError()):
        resp = client.post("/auth/login", json={"username": "alice", "password": "wrong-password"})

    assert resp.status_code == 401
    assert resp.json() == {"error": {"message": "Invalid credentials."}}


def test_login_missing_fields_returns_422() -> None:
    resp = client.post("/auth/login", json={"username": "alice"})
    assert resp.status_code == 422
