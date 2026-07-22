"""Unit tests for app.api.deps.get_current_user."""

import pytest
from fastapi.security import HTTPAuthorizationCredentials

from app.api.deps import CurrentUser, get_current_user
from app.core.errors import AuthError
from app.core.security import create_access_token


def _bearer(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_get_current_user_returns_identity_for_valid_token() -> None:
    token = create_access_token(subject="7", role="admin", expires_minutes=10)

    current = get_current_user(_bearer(token))

    assert current == CurrentUser(user_id=7, role="admin")


def test_get_current_user_rejects_missing_credentials() -> None:
    with pytest.raises(AuthError):
        get_current_user(None)


def test_get_current_user_rejects_tampered_token() -> None:
    token = create_access_token(subject="7", role="admin", expires_minutes=10)
    tampered = token[:-1] + ("y" if token[-1] != "y" else "z")

    with pytest.raises(AuthError):
        get_current_user(_bearer(tampered))


def test_get_current_user_rejects_expired_token() -> None:
    token = create_access_token(subject="7", role="admin", expires_minutes=-1)

    with pytest.raises(AuthError):
        get_current_user(_bearer(token))


def test_get_current_user_rejects_non_numeric_subject() -> None:
    token = create_access_token(subject="not-a-number", role="admin", expires_minutes=10)

    with pytest.raises(AuthError):
        get_current_user(_bearer(token))
