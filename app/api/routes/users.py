"""POST/PUT/DELETE /users — admin-only user management.

Every route requires the caller's role to be 'admin', enforced via
require_role from app.core.rbac.
"""

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser
from app.core.rbac import require_role
from app.schemas.user import SetPasswordRequest, UserCreate, UserOut, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])

_require_admin = require_role("admin")


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate, current_user: CurrentUser = Depends(_require_admin)
) -> UserOut:
    """Create a new user."""
    new_id = user_service.create_user(payload, actor_user_id=current_user.user_id)
    return UserOut(user_id=new_id, username=payload.username, role=payload.role, is_active=True)


@router.put("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def update_user(
    user_id: int, payload: UserUpdate, current_user: CurrentUser = Depends(_require_admin)
) -> None:
    """Update an existing user."""
    user_service.update_user(user_id, payload, actor_user_id=current_user.user_id)


@router.put("/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT)
def set_user_password(
    user_id: int,
    payload: SetPasswordRequest,
    current_user: CurrentUser = Depends(_require_admin),
) -> None:
    """Set a new password for a user."""
    user_service.set_password(user_id, payload.password, actor_user_id=current_user.user_id)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, current_user: CurrentUser = Depends(_require_admin)) -> None:
    """Deactivate a user."""
    user_service.deactivate_user(user_id, actor_user_id=current_user.user_id)
