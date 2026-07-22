"""Route tests for POST/PUT/DELETE /users (mocked user_service, mocked auth dependency)."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.api.deps import CurrentUser, get_current_user
from app.main import app

client = TestClient(app)

_ADMIN = CurrentUser(user_id=1, role="admin")
_VIEWER = CurrentUser(user_id=2, role="viewer")


@pytest.fixture(autouse=True)
def _override_current_user():
    app.dependency_overrides[get_current_user] = lambda: _ADMIN
    yield
    app.dependency_overrides.pop(get_current_user, None)


def test_create_user_returns_created_user() -> None:
    with patch("app.api.routes.users.user_service.create_user", return_value=42) as mock_create:
        resp = client.post(
            "/users", json={"username": "bob", "password": "password123", "role": "viewer"}
        )

    assert resp.status_code == 201
    assert resp.json() == {"user_id": 42, "username": "bob", "role": "viewer", "is_active": True}
    assert mock_create.call_args[1]["actor_user_id"] == 1


def test_update_user_returns_204() -> None:
    with patch("app.api.routes.users.user_service.update_user") as mock_update:
        resp = client.put("/users/42", json={"username": "bob2"})

    assert resp.status_code == 204
    args, kwargs = mock_update.call_args
    assert args[0] == 42
    assert kwargs["actor_user_id"] == 1


def test_set_password_returns_204() -> None:
    with patch("app.api.routes.users.user_service.set_password") as mock_set:
        resp = client.put("/users/42/password", json={"password": "new-password123"})

    assert resp.status_code == 204
    mock_set.assert_called_once_with(42, "new-password123", actor_user_id=1)


def test_delete_user_returns_204() -> None:
    with patch("app.api.routes.users.user_service.deactivate_user") as mock_delete:
        resp = client.delete("/users/42")

    assert resp.status_code == 204
    mock_delete.assert_called_once_with(42, actor_user_id=1)


def test_create_user_without_token_returns_401() -> None:
    app.dependency_overrides.pop(get_current_user, None)

    resp = client.post(
        "/users", json={"username": "bob", "password": "password123", "role": "viewer"}
    )

    assert resp.status_code == 401
    assert resp.json() == {"error": {"message": "Invalid credentials."}}


def test_create_user_as_viewer_returns_403() -> None:
    app.dependency_overrides[get_current_user] = lambda: _VIEWER

    resp = client.post(
        "/users", json={"username": "bob", "password": "password123", "role": "viewer"}
    )

    assert resp.status_code == 403
    assert resp.json() == {"error": {"message": "You do not have permission to perform this action."}}


def test_update_user_as_viewer_returns_403() -> None:
    app.dependency_overrides[get_current_user] = lambda: _VIEWER

    resp = client.put("/users/42", json={"username": "bob2"})

    assert resp.status_code == 403


def test_set_password_as_viewer_returns_403() -> None:
    app.dependency_overrides[get_current_user] = lambda: _VIEWER

    resp = client.put("/users/42/password", json={"password": "new-password123"})

    assert resp.status_code == 403


def test_delete_user_as_viewer_returns_403() -> None:
    app.dependency_overrides[get_current_user] = lambda: _VIEWER

    resp = client.delete("/users/42")

    assert resp.status_code == 403
