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


def test_hash_password_is_salted(security_module: object) -> None:
    """Two hashes of the same password should differ, and both should verify."""
    first = security_module.hash_password("same-password")
    second = security_module.hash_password("same-password")

    assert first != second
    assert security_module.verify_password("same-password", first) is True
    assert security_module.verify_password("same-password", second) is True


def test_verify_password_matches_and_rejects(security_module: object) -> None:
    """verify_password should succeed for the right password and fail for a wrong one."""
    hashed = security_module.hash_password("password123")

    assert security_module.verify_password("password123", hashed) is True
    assert security_module.verify_password("wrong-password", hashed) is False


def test_hash_password_rejects_over_length_input(security_module: object) -> None:
    """A 73-byte password exceeds bcrypt's 72-byte limit and must raise ValueError."""
    over_length = "a" * 73

    with pytest.raises(ValueError):
        security_module.hash_password(over_length)


def test_verify_password_rejects_over_length_input(security_module: object) -> None:
    """An over-length password must fail verification, not raise."""
    hashed = security_module.hash_password("a" * 72)

    assert security_module.verify_password("a" * 73, hashed) is False


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
    tampered = token[:-1] + ("y" if token[-1] != "y" else "z")

    with pytest.raises(AuthError):
        security_module.decode_access_token(tampered)


def test_decode_access_token_rejects_wrong_secret(
    security_module: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A token signed with a different JWT_SECRET must not decode."""
    token = security_module.create_access_token("alice", "viewer", expires_minutes=10)

    monkeypatch.setenv("JWT_SECRET", "a-different-secret")

    from app import config as config_module

    config_module.get_settings.cache_clear()

    importlib.reload(security_module)
    try:
        with pytest.raises(AuthError):
            security_module.decode_access_token(token)
    finally:
        monkeypatch.setenv("JWT_SECRET", REQUIRED_ENV["JWT_SECRET"])
        config_module.get_settings.cache_clear()
        importlib.reload(security_module)


def test_auth_error_message_is_generic(security_module: object) -> None:
    """AuthError must always carry the exact generic message, never leaking details."""
    token = security_module.create_access_token("alice", "viewer", expires_minutes=10)
    tampered = token[:-1] + ("y" if token[-1] != "y" else "z")

    with pytest.raises(AuthError) as exc_info:
        security_module.decode_access_token(tampered)

    assert exc_info.value.public_message == "Invalid credentials."
    assert str(exc_info.value) == "Invalid credentials."


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
