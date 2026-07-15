"""Unit tests for app.core.security."""

import importlib
import logging
from collections.abc import Iterator

import pytest

from app.core.errors import AuthError


REQUIRED_ENV = {
    "APP_DB_CONN": "Driver={ODBC Driver 17 for SQL Server};Server=x;Database=y;UID=u;PWD=p;",
    "JWT_SECRET": "test-secret",
    "JWT_EXPIRE_MINUTES": "60",
    "CRED_ENCRYPTION_KEY": "g4XK4f1nWzQ3u2kR8xYf2vT2Q6C7p4nVb3mL9r2t4d8=",
}


@pytest.fixture()
def security_module(monkeypatch: pytest.MonkeyPatch) -> Iterator[object]:
    """Reload app.core.security with test environment values."""
    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)

    from app import config as config_module

    config_module.get_settings.cache_clear()

    from app.core import security as security_module

    importlib.reload(security_module)
    yield security_module
    importlib.reload(security_module)


def test_hash_password_creates_bcrypt_hash(security_module: object) -> None:
    """hash_password should return a bcrypt hash that differs from the plaintext input."""
    hashed = security_module.hash_password("password123")

    assert hashed != "password123"
    assert hashed.startswith("$2")


def test_verify_password_matches_and_rejects(security_module: object) -> None:
    """verify_password should succeed for the right password and fail for a wrong one."""
    hashed = security_module.hash_password("password123")

    assert security_module.verify_password("password123", hashed) is True
    assert security_module.verify_password("wrong-password", hashed) is False


def test_hash_password_is_salted(security_module: object) -> None:
    """Two hashes of the same password should differ because bcrypt salts them."""
    first = security_module.hash_password("same-password")
    second = security_module.hash_password("same-password")

    assert first != second


def test_create_and_decode_access_token_round_trip(security_module: object) -> None:
    """JWT create/decode should preserve subject and role claims."""
    token = security_module.create_access_token("alice", "admin", expires_minutes=30)
    payload = security_module.decode_access_token(token)

    assert payload["sub"] == "alice"
    assert payload["role"] == "admin"


def test_decode_access_token_rejects_expired_token(security_module: object) -> None:
    """Expired tokens should raise AuthError."""
    token = security_module.create_access_token("alice", "viewer", expires_minutes=-1)

    with pytest.raises(AuthError):
        security_module.decode_access_token(token)


def test_decode_access_token_rejects_tampered_token(security_module: object) -> None:
    """Tampered tokens should raise AuthError."""
    token = security_module.create_access_token("alice", "viewer", expires_minutes=10)
    tampered = token[:-1] + "x"

    with pytest.raises(AuthError):
        security_module.decode_access_token(tampered)


def test_security_functions_do_not_log_secrets(caplog: pytest.LogCaptureFixture, security_module: object) -> None:
    """Password, token, and secret values should not appear in logs or error messages."""
    caplog.set_level(logging.ERROR)
    password = "secret-password"
    token = security_module.create_access_token("alice", "viewer", expires_minutes=5)

    with pytest.raises(AuthError):
        security_module.decode_access_token(token[:-1] + "x")

    assert password not in caplog.text
    assert token not in caplog.text
    assert "test-secret" not in caplog.text
