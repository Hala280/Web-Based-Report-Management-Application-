"""Structured logging configuration for the application."""

import logging
import sys

from app.config import get_settings

_LOG_FORMAT = (
    '{"time":"%(asctime)s","level":"%(levelname)s",'
    '"logger":"%(name)s","message":"%(message)s"}'
)

_configured = False


def configure_logging() -> None:
    """Configure the root logger once, using LOG_LEVEL from settings."""
    global _configured
    if _configured:
        return

    settings = get_settings()
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))

    root = logging.getLogger()
    root.setLevel(settings.LOG_LEVEL)
    root.handlers = [handler]

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger, configuring logging on first use."""
    configure_logging()
    return logging.getLogger(name)
