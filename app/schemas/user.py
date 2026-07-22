"""Pydantic request/response models for authentication and user management.

UserOut never includes PasswordHash — password hashes must never leave the
service layer, let alone be serialized back to a client.
"""

from pydantic import BaseModel, Field

_ROLE_PATTERN = r"^(admin|viewer)$"


class LoginRequest(BaseModel):
    """Credentials submitted to POST /auth/login."""

    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=72)


class TokenResponse(BaseModel):
    """JWT access token returned on successful login."""

    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    """Payload for POST /users."""

    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=72)
    role: str = Field(pattern=_ROLE_PATTERN)


class UserUpdate(BaseModel):
    """Payload for PUT /users/{user_id}.

    All fields are optional so a caller can update only what changed.
    """

    username: str | None = Field(default=None, min_length=1, max_length=100)
    role: str | None = Field(default=None, pattern=_ROLE_PATTERN)
    is_active: bool | None = None


class SetPasswordRequest(BaseModel):
    """Payload for PUT /users/{user_id}/password."""

    password: str = Field(min_length=8, max_length=72)


class UserOut(BaseModel):
    """Public representation of a user — never carries PasswordHash."""

    user_id: int
    username: str
    role: str
    is_active: bool
