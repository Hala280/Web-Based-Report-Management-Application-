"""pyodbc connection management for ReportManagementDB.

This module owns raw connection lifecycle only. It never builds or executes
SQL text — see app/db/proc.py for the stored-procedure/function callers.
"""

import time
from collections.abc import Iterator
from contextlib import contextmanager

import pyodbc

from app.config import get_settings
from app.core.errors import AppError
from app.core.logging_config import get_logger

logger = get_logger(__name__)

CONNECT_TIMEOUT_SECONDS = 5
MAX_CONNECT_ATTEMPTS = 2
RETRY_BACKOFF_SECONDS = 0.5

# SQLSTATE prefixes considered transient — safe to retry a fresh connection attempt.
_TRANSIENT_SQLSTATES = {"08001", "08S01", "HYT00", "HYT01"}


class DatabaseConnectionError(AppError):
    """Raised when a connection to ReportManagementDB cannot be established."""

    status_code = 503
    public_message = "The database is temporarily unavailable."


def _is_transient(exc: pyodbc.Error) -> bool:
    """Return True if the pyodbc error's SQLSTATE indicates a transient failure."""
    sqlstate = exc.args[0] if exc.args else ""
    return sqlstate in _TRANSIENT_SQLSTATES


def _connect() -> pyodbc.Connection:
    """Open a new pyodbc connection, retrying once on a transient failure."""
    settings = get_settings()

    for attempt in range(1, MAX_CONNECT_ATTEMPTS + 1):
        try:
            return pyodbc.connect(settings.APP_DB_CONN, timeout=CONNECT_TIMEOUT_SECONDS)
        except pyodbc.Error as exc:
            if attempt < MAX_CONNECT_ATTEMPTS and _is_transient(exc):
                logger.warning("Transient DB connection failure on attempt %s, retrying.", attempt)
                time.sleep(RETRY_BACKOFF_SECONDS)
                continue
            logger.error("Failed to connect to database on attempt %s.", attempt)
            raise DatabaseConnectionError() from exc

    raise DatabaseConnectionError()  # unreachable: loop always returns or raises above


@contextmanager
def get_connection() -> Iterator[pyodbc.Connection]:
    """Yield a pyodbc connection to ReportManagementDB, always closed on exit."""
    conn = _connect()
    try:
        yield conn
    finally:
        conn.close()
