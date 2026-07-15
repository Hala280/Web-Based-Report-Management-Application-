"""Security primitives for password hashing and JWT handling."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt

from app.config import get_settings
from app.core.errors import AuthError
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def hash_password(plain: str) -> str:
    """Return a bcrypt hash for the supplied plaintext password."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Return True when the plaintext password matches the supplied bcrypt hash."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def _base64url_decode(value: str) -> bytes:
    """Decode a base64url-encoded string to bytes."""
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def create_access_token(subject: str, role: str, expires_minutes: int | None = None) -> str:
    """Create a signed JWT access token for the supplied subject and role."""
    settings = get_settings()
    minutes = expires_minutes if expires_minutes is not None else settings.JWT_EXPIRE_MINUTES

    payload = {
        "sub": subject,
        "role": role,
        "exp": int((datetime.now(timezone.utc) + timedelta(minutes=minutes)).timestamp()),
    }
    header = {"alg": "HS256", "typ": "JWT"}

    header_segment = base64.urlsafe_b64encode(json.dumps(header, separators=(",", ":")).encode("utf-8")).rstrip(b"=").decode("ascii")
    payload_segment = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")).rstrip(b"=").decode("ascii")
    signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
    signature = hmac.new(settings.JWT_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_segment = base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")
    return f"{header_segment}.{payload_segment}.{signature_segment}"


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT access token, raising AuthError on failure."""
    settings = get_settings()

    try:
        header_segment, payload_segment, signature_segment = token.split(".")
    except ValueError as exc:
        logger.warning("Failed to decode access token")
        raise AuthError("Invalid credentials.") from exc

    try:
        header_bytes = _base64url_decode(header_segment)
        payload_bytes = _base64url_decode(payload_segment)
    except (ValueError, TypeError) as exc:
        logger.warning("Failed to decode access token")
        raise AuthError("Invalid credentials.") from exc

    try:
        header = json.loads(header_bytes.decode("utf-8"))
        payload = json.loads(payload_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        logger.warning("Failed to decode access token")
        raise AuthError("Invalid credentials.") from exc

    if header.get("alg") != "HS256":
        logger.warning("Access token algorithm rejected")
        raise AuthError("Invalid credentials.")

    signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
    expected_signature = base64.urlsafe_b64encode(
        hmac.new(settings.JWT_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
    ).rstrip(b"=")
    if not hmac.compare_digest(signature_segment.encode("ascii"), expected_signature):
        logger.warning("Access token signature rejected")
        raise AuthError("Invalid credentials.")

    if not payload.get("sub") or not payload.get("role"):
        logger.warning("Access token missing required claims")
        raise AuthError("Invalid credentials.")

    exp = payload.get("exp")
    if isinstance(exp, (int, float)) and datetime.now(timezone.utc).timestamp() >= float(exp):
        logger.warning("Access token expired")
        raise AuthError("Invalid credentials.")

    return payload
