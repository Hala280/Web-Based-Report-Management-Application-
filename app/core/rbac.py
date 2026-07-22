"""Role-based access control dependencies.

Mirrors the DB-side rule enforced by dbo.ufn_IsActionAllowed: admins may
perform every action; viewers are limited to executing and downloading
reports. Login requires no role at all (it happens before a token exists).
"""

from collections.abc import Callable

from fastapi import Depends

from app.api.deps import CurrentUser, get_current_user
from app.core.errors import PermissionError

ADMIN = "admin"
VIEWER = "viewer"

# Action -> roles allowed to perform it. Mirrors dbo.ufn_IsActionAllowed.
_ACTION_ROLES: dict[str, set[str]] = {
    "manage_users": {ADMIN},
    "manage_reports": {ADMIN},
    "manage_connections": {ADMIN},
    "manage_schedules": {ADMIN},
    "execute_report": {ADMIN, VIEWER},
    "download_report": {ADMIN, VIEWER},
}


def require_role(*roles: str) -> Callable[[CurrentUser], CurrentUser]:
    """Build a dependency that 403s unless the current user's role is one of `roles`."""
    allowed = set(roles)

    def _dependency(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.role not in allowed:
            raise PermissionError()
        return current_user

    return _dependency


def require_permission(action: str) -> Callable[[CurrentUser], CurrentUser]:
    """Build a dependency that 403s unless the current user's role may perform `action`.

    `action` must be one of the keys in _ACTION_ROLES; an unknown action is a
    programming error, not a runtime/client condition, so it raises
    ValueError immediately rather than silently denying everyone.
    """
    try:
        allowed_roles = _ACTION_ROLES[action]
    except KeyError:
        raise ValueError(f"Unknown RBAC action: {action!r}") from None

    def _dependency(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.role not in allowed_roles:
            raise PermissionError()
        return current_user

    return _dependency
