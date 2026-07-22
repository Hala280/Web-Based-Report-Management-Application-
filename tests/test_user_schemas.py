"""Unit tests for app.schemas.user."""

import pytest
from pydantic import ValidationError

from app.schemas.user import (
    LoginRequest,
    SetPasswordRequest,
    TokenResponse,
    UserCreate,
    UserOut,
    UserUpdate,
)


def test_login_request_requires_username_and_password() -> None:
    with pytest.raises(ValidationError):
        LoginRequest(username="", password="secret")


def test_token_response_defaults_to_bearer() -> None:
    token = TokenResponse(access_token="abc.def.ghi")
    assert token.token_type == "bearer"


def test_user_create_accepts_admin_and_viewer_roles() -> None:
    UserCreate(username="alice", password="password123", role="admin")
    UserCreate(username="bob", password="password123", role="viewer")


def test_user_create_rejects_unknown_role() -> None:
    with pytest.raises(ValidationError):
        UserCreate(username="alice", password="password123", role="superadmin")


def test_user_create_rejects_short_password() -> None:
    with pytest.raises(ValidationError):
        UserCreate(username="alice", password="short", role="viewer")


def test_user_update_fields_are_all_optional() -> None:
    update = UserUpdate()
    assert update.username is None
    assert update.role is None
    assert update.is_active is None


def test_user_update_rejects_unknown_role() -> None:
    with pytest.raises(ValidationError):
        UserUpdate(role="superadmin")


def test_set_password_request_rejects_short_password() -> None:
    with pytest.raises(ValidationError):
        SetPasswordRequest(password="short")


def test_user_out_never_has_password_field() -> None:
    assert "password" not in UserOut.model_fields
    assert "password_hash" not in UserOut.model_fields


def test_user_out_round_trip() -> None:
    user = UserOut(user_id=1, username="alice", role="admin", is_active=True)
    assert user.model_dump() == {
        "user_id": 1,
        "username": "alice",
        "role": "admin",
        "is_active": True,
    }
