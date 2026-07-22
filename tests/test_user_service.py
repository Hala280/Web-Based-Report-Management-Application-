"""Unit tests for app.services.user_service (mocked users_repo)."""

from unittest.mock import patch

from app.schemas.user import UserCreate, UserUpdate
from app.services import user_service


def test_create_user_hashes_password_before_storing() -> None:
    payload = UserCreate(username="alice", password="password123", role="viewer")

    with (
        patch("app.services.user_service.users_repo.create_user", return_value=5) as mock_create,
        patch("app.services.user_service.users_repo.add_log") as mock_log,
    ):
        new_id = user_service.create_user(payload, actor_user_id=1)

    assert new_id == 5
    called_username, called_hash, called_role = mock_create.call_args[0]
    assert called_username == "alice"
    assert called_hash != "password123"
    assert called_hash.startswith("$2")
    assert called_role == "viewer"
    mock_log.assert_called_once_with(1, "USER_CREATE", entity_type="user")


def test_update_user_delegates_to_repo_and_logs() -> None:
    payload = UserUpdate(username="alice2", role=None, is_active=False)

    with (
        patch("app.services.user_service.users_repo.update_user") as mock_update,
        patch("app.services.user_service.users_repo.add_log") as mock_log,
    ):
        user_service.update_user(5, payload, actor_user_id=1)

    mock_update.assert_called_once_with(5, "alice2", None, False)
    mock_log.assert_called_once_with(1, "USER_UPDATE", entity_type="user")


def test_set_password_hashes_before_storing() -> None:
    with (
        patch("app.services.user_service.users_repo.set_password") as mock_set,
        patch("app.services.user_service.users_repo.add_log") as mock_log,
    ):
        user_service.set_password(5, "new-password123", actor_user_id=1)

    called_user_id, called_hash = mock_set.call_args[0]
    assert called_user_id == 5
    assert called_hash != "new-password123"
    assert called_hash.startswith("$2")
    mock_log.assert_called_once_with(1, "USER_SET_PASSWORD", entity_type="user")


def test_deactivate_user_delegates_to_repo_and_logs() -> None:
    with (
        patch("app.services.user_service.users_repo.delete_user") as mock_delete,
        patch("app.services.user_service.users_repo.add_log") as mock_log,
    ):
        user_service.deactivate_user(5, actor_user_id=1)

    mock_delete.assert_called_once_with(5)
    mock_log.assert_called_once_with(1, "USER_DEACTIVATE", entity_type="user")
