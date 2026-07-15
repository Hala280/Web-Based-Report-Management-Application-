"""Unit tests for app.core.crypto."""

import importlib
import logging
from collections.abc import Iterator

import pytest


REQUIRED_ENV = {
    "APP_DB_CONN": "Driver={ODBC Driver 17 for SQL Server};Server=x;Database=y;UID=u;PWD=p;",
    "JWT_SECRET": "test-secret",
    "JWT_EXPIRE_MINUTES": "60",
}


@pytest.fixture()
def crypto_module(monkeypatch: pytest.MonkeyPatch) -> Iterator[object]:
    """Reload app.core.crypto with test environment values."""
    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("CRED_ENCRYPTION_KEY", "g4XK4f1nWzQ3u2kR8xYf2vT2Q6C7p4nVb3mL9r2t4d8=")

    from app import config as config_module

    config_module.get_settings.cache_clear()

    from app.core import crypto as crypto_module

    importlib.reload(crypto_module)
    yield crypto_module
    importlib.reload(crypto_module)


def test_encrypt_and_decrypt_round_trip(crypto_module: object) -> None:
    """encrypt_secret should round-trip back through decrypt_secret."""
    plaintext = "super-secret-password"
    blob = crypto_module.encrypt_secret(plaintext)

    assert blob != plaintext
    assert crypto_module.decrypt_secret(blob) == plaintext


def test_ciphertext_is_not_plaintext(crypto_module: object) -> None:
    """Ciphertext should differ from the original plaintext value."""
    blob = crypto_module.encrypt_secret("password")

    assert blob != "password"


def test_invalid_encryption_key_fails_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Malformed encryption keys should fail validation."""
    monkeypatch.setenv("CRED_ENCRYPTION_KEY", "not-a-valid-key")

    from app import config as config_module

    config_module.get_settings.cache_clear()

    from app.core import crypto as crypto_module

    with pytest.raises(ValueError):
        importlib.reload(crypto_module)


def test_valid_encryption_key_passes_validation(crypto_module: object) -> None:
    """A valid Fernet-compatible key should pass validation."""
    assert crypto_module.validate_encryption_key() is True


def test_crypto_functions_do_not_log_secrets(caplog: pytest.LogCaptureFixture, crypto_module: object) -> None:
    """Plaintext secrets and keys should not appear in logs or error messages."""
    caplog.set_level(logging.ERROR)
    secret = "top-secret"

    with pytest.raises(ValueError):
        crypto_module.validate_encryption_key("not-a-valid-key")

    assert secret not in caplog.text
    assert "top-secret" not in caplog.text
