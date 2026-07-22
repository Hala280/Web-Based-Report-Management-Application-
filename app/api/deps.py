"""FastAPI dependencies shared across routes."""

from dataclasses import dataclass

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.errors import AuthError
from app.core.security import decode_access_token

_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    """The authenticated caller, decoded from a bearer JWT."""

    user_id: int
    role: str


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> CurrentUser:
    """Decode the bearer JWT and return the authenticated caller's identity.

    Only proves the caller holds a valid, unexpired token signed by this
    server. Role-based authorization (e.g. requiring role == "admin") is not
    enforced here — see app.core.rbac.require_role / require_permission for
    that. Raises AuthError (401) for a missing, malformed, or invalid token.
    """
    if credentials is None:
        raise AuthError()

    payload = decode_access_token(credentials.credentials)
    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise AuthError() from exc

    return CurrentUser(user_id=user_id, role=payload.get("role", ""))
