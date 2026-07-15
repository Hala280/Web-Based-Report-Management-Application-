"""Symmetric encryption helpers for protecting stored secrets."""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def validate_encryption_key(key: str | None = None) -> bool:
    """Validate that the supplied key is a usable Fernet key."""
    candidate = key if key is not None else get_settings().CRED_ENCRYPTION_KEY
    try:
        Fernet(candidate.encode("utf-8"))
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.warning("Invalid encryption key supplied")
        raise ValueError("Invalid encryption key") from exc
    return True


validate_encryption_key()


def _get_fernet() -> Fernet:
    """Build a Fernet instance from the configured encryption key."""
    settings = get_settings()
    return Fernet(settings.CRED_ENCRYPTION_KEY.encode("utf-8"))


def encrypt_secret(plain: str) -> bytes:
    """Encrypt a plaintext secret with the configured Fernet key."""
    validate_encryption_key()
    return _get_fernet().encrypt(plain.encode("utf-8"))


def decrypt_secret(blob: bytes) -> str:
    """Decrypt a stored Fernet ciphertext and return the plaintext string."""
    validate_encryption_key()
    try:
        return _get_fernet().decrypt(blob).decode("utf-8")
    except InvalidToken as exc:
        logger.warning("Failed to decrypt secret")
        raise ValueError("Invalid secret payload") from exc
