"""Unit tests for app.core.logging_config (no I/O beyond stdout stream handler)."""

import importlib
import logging

import pytest


REQUIRED_ENV = {
    "APP_DB_CONN": "Driver={ODBC Driver 17 for SQL Server};Server=x;Database=y;UID=u;PWD=p;",
    "JWT_SECRET": "test-secret",
    "JWT_EXPIRE_MINUTES": "60",
    "CRED_ENCRYPTION_KEY": "test-key",
}


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch):
    """Provide required settings env vars and reload the module for a clean state."""
    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    from app import config as config_module

    config_module.get_settings.cache_clear()

    from app.core import logging_config as logging_config_module

    importlib.reload(logging_config_module)
    yield logging_config_module
    importlib.reload(logging_config_module)


def test_get_logger_returns_named_logger(_clean_env) -> None:
    """get_logger should return a Logger instance with the requested name."""
    logger = _clean_env.get_logger("my.module")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "my.module"


def test_configure_logging_sets_root_level_from_settings(_clean_env) -> None:
    """Root logger level should match LOG_LEVEL from settings after configuration."""
    _clean_env.configure_logging()
    assert logging.getLogger().level == logging.DEBUG


def test_configure_logging_is_idempotent(_clean_env) -> None:
    """Calling configure_logging multiple times should not duplicate handlers."""
    _clean_env.configure_logging()
    _clean_env.configure_logging()
    _clean_env.configure_logging()
    assert len(logging.getLogger().handlers) == 1
