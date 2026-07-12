"""Unit tests for app.config.Settings (no I/O, no live database)."""

import pytest
from pydantic import ValidationError

from app.config import Settings


REQUIRED_ENV = {
    "APP_DB_CONN": "Driver={ODBC Driver 17 for SQL Server};Server=x;Database=y;UID=u;PWD=p;",
    "JWT_SECRET": "test-secret",
    "JWT_EXPIRE_MINUTES": "60",
    "CRED_ENCRYPTION_KEY": "test-key",
}


def test_settings_loads_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Settings should populate all fields from environment variables."""
    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    settings = Settings(_env_file=None)

    assert settings.APP_DB_CONN == REQUIRED_ENV["APP_DB_CONN"]
    assert settings.JWT_SECRET == "test-secret"
    assert settings.JWT_EXPIRE_MINUTES == 60
    assert settings.CRED_ENCRYPTION_KEY == "test-key"
    assert settings.LOG_LEVEL == "DEBUG"


def test_settings_log_level_defaults_to_info(monkeypatch: pytest.MonkeyPatch) -> None:
    """LOG_LEVEL should default to INFO when not set."""
    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    settings = Settings(_env_file=None)

    assert settings.LOG_LEVEL == "INFO"


def test_settings_missing_required_field_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing a required setting (e.g. JWT_SECRET) should raise ValidationError."""
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.setenv("APP_DB_CONN", REQUIRED_ENV["APP_DB_CONN"])
    monkeypatch.setenv("JWT_EXPIRE_MINUTES", "60")
    monkeypatch.setenv("CRED_ENCRYPTION_KEY", "test-key")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)
