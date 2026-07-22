"""Password hashing and JWT access-token primitives.

No business logic and no DB access here — only cryptographic operations
consumed by the authentication layer (Phase 3) and the connection registry
(Phase 5).
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.config import get_settings
from app.core.errors import AuthError

_JWT_ALGORITHM = "HS256"

# bcrypt silently truncates the input at 72 bytes; anything longer is
# rejected explicitly rather than being silently weakened.
_BCRYPT_MAX_BYTES = 72


def hash_password(plain: str) -> str:
    """Hash a plaintext password with a freshly generated bcrypt salt."""
    encoded = plain.encode("utf-8")
    if len(encoded) > _BCRYPT_MAX_BYTES:
        raise ValueError("Password exceeds the 72-byte bcrypt input limit.")
    hashed = bcrypt.hashpw(encoded, bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Check a plaintext password against a bcrypt hash, without raising."""
    encoded = plain.encode("utf-8")
    if len(encoded) > _BCRYPT_MAX_BYTES:
        return False
    try:
        return bcrypt.checkpw(encoded, hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(subject: str, role: str, expires_minutes: int | None = None) -> str:
    """Create a signed JWT embedding `sub`, `role`, and `exp`."""
    settings = get_settings()
    minutes = expires_minutes if expires_minutes is not None else settings.JWT_EXPIRE_MINUTES
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    payload = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=_JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Verify a JWT's signature and expiry, returning its payload.

    Raises AuthError (generic — no reason disclosed) for any invalid,
    tampered, or expired token.
    """
    settings = get_settings()
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[_JWT_ALGORITHM])
    except JWTError as exc:
        raise AuthError() from exc
