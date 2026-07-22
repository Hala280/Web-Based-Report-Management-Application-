"""Unit tests for app.services.auth_service (mocked users_repo)."""

from unittest.mock import patch

import pytest

from app.core.errors import AuthError
from app.core.security import hash_password
from app.services import auth_service


def _user(**overrides: object) -> dict:
    base = {
        "UserId": 1,
        "Username": "alice",
        "PasswordHash": hash_password("correct-password"),
        "Role": "admin",
        "IsActive": True,
    }
    base.update(overrides)
    return base


def test_authenticate_returns_token_for_valid_credentials() -> None:
    with (
        patch("app.services.auth_service.users_repo.get_user_for_login", return_value=_user()),
        patch("app.services.auth_service.users_repo.add_log") as mock_log,
    ):
        token = auth_service.authenticate("alice", "correct-password")

    assert isinstance(token, str) and token
    mock_log.assert_called_once_with(1, "LOGIN_SUCCESS", entity_type="user")


def test_authenticate_rejects_wrong_password_with_generic_error() -> None:
    with (
        patch("app.services.auth_service.users_repo.get_user_for_login", return_value=_user()),
        patch("app.services.auth_service.users_repo.add_log") as mock_log,
    ):
        with pytest.raises(AuthError) as exc_info:
            auth_service.authenticate("alice", "wrong-password")

    assert exc_info.value.public_message == "Invalid credentials."
    mock_log.assert_called_once_with(1, "LOGIN_FAILED", entity_type="user")


def test_authenticate_rejects_unknown_username_with_generic_error() -> None:
    with (
        patch("app.services.auth_service.users_repo.get_user_for_login", return_value=None),
        patch("app.services.auth_service.users_repo.add_log") as mock_log,
    ):
        with pytest.raises(AuthError) as exc_info:
            auth_service.authenticate("ghost", "whatever")

    assert exc_info.value.public_message == "Invalid credentials."
    mock_log.assert_called_once_with(None, "LOGIN_FAILED", entity_type="user")


def test_authenticate_rejects_inactive_user() -> None:
    with (
        patch(
            "app.services.auth_service.users_repo.get_user_for_login",
            return_value=_user(IsActive=False),
        ),
        patch("app.services.auth_service.users_repo.add_log") as mock_log,
    ):
        with pytest.raises(AuthError):
            auth_service.authenticate("alice", "correct-password")

    mock_log.assert_called_once_with(1, "LOGIN_FAILED", entity_type="user")


def test_authenticate_unknown_and_wrong_password_raise_identical_error() -> None:
    """Same message/status for both cases so responses can't be used to enumerate users."""
    with patch("app.services.auth_service.users_repo.get_user_for_login", return_value=None):
        with patch("app.services.auth_service.users_repo.add_log"):
            with pytest.raises(AuthError) as unknown_exc:
                auth_service.authenticate("ghost", "whatever")

    with patch("app.services.auth_service.users_repo.get_user_for_login", return_value=_user()):
        with patch("app.services.auth_service.users_repo.add_log"):
            with pytest.raises(AuthError) as wrong_pw_exc:
                auth_service.authenticate("alice", "wrong-password")

    assert unknown_exc.value.public_message == wrong_pw_exc.value.public_message
    assert unknown_exc.value.status_code == wrong_pw_exc.value.status_code == 401


def test_authenticate_token_embeds_user_id_and_role() -> None:
    from app.core.security import decode_access_token

    with (
        patch("app.services.auth_service.users_repo.get_user_for_login", return_value=_user()),
        patch("app.services.auth_service.users_repo.add_log"),
    ):
        token = auth_service.authenticate("alice", "correct-password")

    payload = decode_access_token(token)
    assert payload["sub"] == "1"
    assert payload["role"] == "admin"
