"""Security primitives for password hashing and JWT handling.

JWT payloads are now encrypted (AES-256-GCM) in addition to being signed
(HMAC-SHA256), so the claims (sub/role/exp) are no longer readable by
simply base64-decoding the token.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import get_settings
from app.core.errors import AuthError
from app.core.logging_config import get_logger

logger = get_logger(__name__)

_NONCE_LEN = 12  # 96-bit nonce, standard for AES-GCM


# --------------------------------------------------------------------------
# Password hashing
# --------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    """Return a bcrypt hash for the supplied plaintext password."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Return True when the plaintext password matches the supplied bcrypt hash."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# --------------------------------------------------------------------------
# base64url helpers
# --------------------------------------------------------------------------

def _base64url_encode(data: bytes) -> str:
    """Encode bytes as unpadded base64url text."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _base64url_decode(value: str) -> bytes:
    """Decode a base64url-encoded string to bytes."""
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


# --------------------------------------------------------------------------
# AES-256-GCM helpers for the payload
# --------------------------------------------------------------------------

def _get_aesgcm() -> AESGCM:
    """Build an AESGCM instance from the configured 32-byte encryption key.

    JWT_ENCRYPTION_KEY must be a base64-encoded 32-byte key, e.g. generated with:
        python -c "import base64, os; print(base64.b64encode(os.urandom(32)).decode())"
    """
    settings = get_settings()
    key = base64.b64decode(settings.JWT_ENCRYPTION_KEY)
    if len(key) != 32:
        raise AuthError("Invalid credentials.")
    return AESGCM(key)


def _encrypt_payload(payload: dict[str, Any]) -> str:
    """JSON-encode and AES-256-GCM encrypt the payload, returning a base64url segment.

    The segment is: base64url(nonce || ciphertext_with_gcm_tag)
    """
    aesgcm = _get_aesgcm()
    nonce = os.urandom(_NONCE_LEN)
    plaintext = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data=None)
    return _base64url_encode(nonce + ciphertext)


def _decrypt_payload(payload_segment: str) -> dict[str, Any]:
    """Reverse of _encrypt_payload. Raises on any decode/auth failure."""
    aesgcm = _get_aesgcm()
    raw = _base64url_decode(payload_segment)
    if len(raw) < _NONCE_LEN:
        raise ValueError("Ciphertext too short")
    nonce, ciphertext = raw[:_NONCE_LEN], raw[_NONCE_LEN:]
    plaintext = aesgcm.decrypt(nonce, ciphertext, associated_data=None)
    return json.loads(plaintext.decode("utf-8"))


# --------------------------------------------------------------------------
# JWT creation / validation
# --------------------------------------------------------------------------

def create_access_token(subject: str, role: str, expires_minutes: int | None = None) -> str:
    """Create a signed *and* encrypted JWT access token for the supplied subject and role."""
    settings = get_settings()
    minutes = expires_minutes if expires_minutes is not None else settings.JWT_EXPIRE_MINUTES

    payload = {
        "sub": subject,
        "role": role,
        "exp": int((datetime.now(timezone.utc) + timedelta(minutes=minutes)).timestamp()),
    }
    header = {"alg": "HS256", "typ": "JWT", "enc": "A256GCM"}

    header_segment = _base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_segment = _encrypt_payload(payload)

    signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
    signature = hmac.new(settings.JWT_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_segment = _base64url_encode(signature)

    return f"{header_segment}.{payload_segment}.{signature_segment}"


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode, decrypt, and validate a JWT access token, raising AuthError on failure."""
    settings = get_settings()

    try:
        header_segment, payload_segment, signature_segment = token.split(".")
    except ValueError as exc:
        logger.warning("Failed to decode access token")
        raise AuthError("Invalid credentials.") from exc

    try:
        header_bytes = _base64url_decode(header_segment)
    except (ValueError, TypeError) as exc:
        logger.warning("Failed to decode access token")
        raise AuthError("Invalid credentials.") from exc

    try:
        header = json.loads(header_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        logger.warning("Failed to decode access token")
        raise AuthError("Invalid credentials.") from exc

    if header.get("alg") != "HS256":
        logger.warning("Access token algorithm rejected")
        raise AuthError("Invalid credentials.")

    if header.get("enc") != "A256GCM":
        logger.warning("Access token encryption scheme rejected")
        raise AuthError("Invalid credentials.")

    # Verify the signature BEFORE attempting to decrypt. This means a forged/
    # tampered token is rejected on the cheap HMAC check first, rather than
    # spending effort attempting an AES-GCM decrypt on attacker-controlled input.
    signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
    expected_signature = base64.urlsafe_b64encode(
        hmac.new(settings.JWT_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
    ).rstrip(b"=")
    if not hmac.compare_digest(signature_segment.encode("ascii"), expected_signature):
        logger.warning("Access token signature rejected")
        raise AuthError("Invalid credentials.")

    try:
        payload = _decrypt_payload(payload_segment)
    except Exception as exc:  # noqa: BLE001 - any decrypt/parse failure means invalid token
        logger.warning("Failed to decrypt access token payload")
        raise AuthError("Invalid credentials.") from exc

    if not payload.get("sub") or not payload.get("role"):
        logger.warning("Access token missing required claims")
        raise AuthError("Invalid credentials.")

    exp = payload.get("exp")
    if isinstance(exp, (int, float)) and datetime.now(timezone.utc).timestamp() >= float(exp):
        logger.warning("Access token expired")
        raise AuthError("Invalid credentials.")

    return payload
