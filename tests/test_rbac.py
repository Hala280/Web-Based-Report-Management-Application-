"""Unit tests for app.core.rbac (require_role / require_permission)."""

import pytest

from app.api.deps import CurrentUser
from app.core.errors import PermissionError
from app.core.rbac import require_permission, require_role

_ADMIN = CurrentUser(user_id=1, role="admin")
_VIEWER = CurrentUser(user_id=2, role="viewer")


def test_require_role_allows_matching_role() -> None:
    dependency = require_role("admin")
    assert dependency(_ADMIN) == _ADMIN


def test_require_role_rejects_non_matching_role() -> None:
    dependency = require_role("admin")
    with pytest.raises(PermissionError):
        dependency(_VIEWER)


def test_require_role_rejection_is_403_with_generic_message() -> None:
    dependency = require_role("admin")
    with pytest.raises(PermissionError) as exc_info:
        dependency(_VIEWER)

    assert exc_info.value.status_code == 403
    assert exc_info.value.public_message == "You do not have permission to perform this action."


def test_require_role_accepts_multiple_roles() -> None:
    dependency = require_role("admin", "viewer")
    assert dependency(_ADMIN) == _ADMIN
    assert dependency(_VIEWER) == _VIEWER


def test_require_permission_manage_users_allows_admin() -> None:
    dependency = require_permission("manage_users")
    assert dependency(_ADMIN) == _ADMIN


def test_require_permission_manage_users_rejects_viewer() -> None:
    dependency = require_permission("manage_users")
    with pytest.raises(PermissionError):
        dependency(_VIEWER)


@pytest.mark.parametrize("action", ["manage_reports", "manage_connections", "manage_schedules"])
def test_require_permission_management_actions_reject_viewer(action: str) -> None:
    dependency = require_permission(action)
    with pytest.raises(PermissionError):
        dependency(_VIEWER)
    assert dependency(_ADMIN) == _ADMIN


@pytest.mark.parametrize("action", ["execute_report", "download_report"])
def test_require_permission_allows_viewer_to_execute_and_download(action: str) -> None:
    dependency = require_permission(action)
    assert dependency(_VIEWER) == _VIEWER
    assert dependency(_ADMIN) == _ADMIN


def test_require_permission_rejects_unknown_action() -> None:
    with pytest.raises(ValueError):
        require_permission("not_a_real_action")
