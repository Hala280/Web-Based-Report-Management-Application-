"""Admin user-management operations: create, update, deactivate, set password.

Passwords are always hashed via app.core.security before reaching the
repository layer — plaintext passwords never reach the database.
"""

from app.core.security import hash_password
from app.repositories import users_repo
from app.schemas.user import UserCreate, UserUpdate

_ENTITY_TYPE_USER = "user"


def create_user(payload: UserCreate, actor_user_id: int) -> int:
    """Create a new user and return its UserId."""
    password_hash = hash_password(payload.password)
    new_id = users_repo.create_user(payload.username, password_hash, payload.role)
    users_repo.add_log(actor_user_id, "USER_CREATE", entity_type=_ENTITY_TYPE_USER)
    return new_id


def update_user(user_id: int, payload: UserUpdate, actor_user_id: int) -> None:
    """Update the given user's mutable fields (unset fields are left unchanged)."""
    users_repo.update_user(user_id, payload.username, payload.role, payload.is_active)
    users_repo.add_log(actor_user_id, "USER_UPDATE", entity_type=_ENTITY_TYPE_USER)


def set_password(user_id: int, new_password: str, actor_user_id: int) -> None:
    """Hash and store a new password for the given user."""
    password_hash = hash_password(new_password)
    users_repo.set_password(user_id, password_hash)
    users_repo.add_log(actor_user_id, "USER_SET_PASSWORD", entity_type=_ENTITY_TYPE_USER)


def deactivate_user(user_id: int, actor_user_id: int) -> None:
    """Deactivate (delete) the given user."""
    users_repo.delete_user(user_id)
    users_repo.add_log(actor_user_id, "USER_DEACTIVATE", entity_type=_ENTITY_TYPE_USER)
