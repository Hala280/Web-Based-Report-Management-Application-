"""Unit tests for app.repositories.users_repo (mocked call_proc/call_proc_scalar)."""

from unittest.mock import patch

from app.repositories import users_repo


def test_get_user_for_login_returns_row_when_found() -> None:
    row = {"UserId": 1, "Username": "alice", "PasswordHash": "$2b$...", "Role": "admin", "IsActive": True}
    with patch("app.repositories.users_repo.call_proc", return_value=[row]) as mock_call:
        result = users_repo.get_user_for_login("alice")

    assert result == row
    mock_call.assert_called_once_with("dbo.usp_GetUserForLogin", {"Username": "alice"})


def test_get_user_for_login_returns_none_when_not_found() -> None:
    with patch("app.repositories.users_repo.call_proc", return_value=[]):
        result = users_repo.get_user_for_login("ghost")

    assert result is None


def test_create_user_returns_new_id() -> None:
    with patch("app.repositories.users_repo.call_proc_scalar", return_value=42) as mock_call:
        new_id = users_repo.create_user("alice", "hashed", "admin")

    assert new_id == 42
    mock_call.assert_called_once_with(
        "dbo.usp_User_Create",
        {"Username": "alice", "PasswordHash": "hashed", "Role": "admin"},
    )


def test_update_user_translates_is_active_true_to_status_active() -> None:
    with patch("app.repositories.users_repo.call_proc") as mock_call:
        users_repo.update_user(1, "alice2", None, True)

    mock_call.assert_called_once_with(
        "dbo.usp_User_Update",
        {"UserId": 1, "Username": "alice2", "Role": None, "Status": "active"},
    )


def test_update_user_translates_is_active_false_to_status_inactive() -> None:
    with patch("app.repositories.users_repo.call_proc") as mock_call:
        users_repo.update_user(1, "alice2", None, False)

    mock_call.assert_called_once_with(
        "dbo.usp_User_Update",
        {"UserId": 1, "Username": "alice2", "Role": None, "Status": "inactive"},
    )


def test_update_user_leaves_status_none_when_is_active_not_provided() -> None:
    with patch("app.repositories.users_repo.call_proc") as mock_call:
        users_repo.update_user(1, None, "admin", None)

    mock_call.assert_called_once_with(
        "dbo.usp_User_Update",
        {"UserId": 1, "Username": None, "Role": "admin", "Status": None},
    )


def test_set_password_calls_proc_with_hash() -> None:
    with patch("app.repositories.users_repo.call_proc") as mock_call:
        users_repo.set_password(1, "new-hash")

    mock_call.assert_called_once_with(
        "dbo.usp_User_SetPassword", {"UserId": 1, "PasswordHash": "new-hash"}
    )


def test_delete_user_calls_proc_with_id() -> None:
    with patch("app.repositories.users_repo.call_proc") as mock_call:
        users_repo.delete_user(7)

    mock_call.assert_called_once_with("dbo.usp_User_Delete", {"UserId": 7})


def test_add_log_calls_proc_with_entity_type() -> None:
    with patch("app.repositories.users_repo.call_proc") as mock_call:
        users_repo.add_log(1, "LOGIN_SUCCESS", entity_type="user")

    mock_call.assert_called_once_with(
        "dbo.usp_Log_Add", {"Action": "LOGIN_SUCCESS", "UserId": 1, "EntityType": "user"}
    )


def test_add_log_allows_none_user_id_for_anonymous_events() -> None:
    with patch("app.repositories.users_repo.call_proc") as mock_call:
        users_repo.add_log(None, "LOGIN_FAILED")

    mock_call.assert_called_once_with(
        "dbo.usp_Log_Add", {"Action": "LOGIN_FAILED", "UserId": None, "EntityType": None}
    )
