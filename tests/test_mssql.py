"""Unit tests for app.db.mssql. pyodbc.connect is fully mocked — no real DB."""

from unittest.mock import MagicMock, patch

import pyodbc
import pytest

from app.db.mssql import DatabaseConnectionError, get_connection


def _pyodbc_error(sqlstate: str) -> pyodbc.Error:
    return pyodbc.Error(sqlstate, f"simulated failure {sqlstate}")


@patch("app.db.mssql.pyodbc.connect")
def test_get_connection_yields_connection_and_closes_it(mock_connect: MagicMock) -> None:
    """A successful connect should be yielded and closed on context exit."""
    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn

    with get_connection() as conn:
        assert conn is mock_conn
        mock_conn.close.assert_not_called()

    mock_conn.close.assert_called_once()


@patch("app.db.mssql.time.sleep")
@patch("app.db.mssql.pyodbc.connect")
def test_get_connection_retries_once_on_transient_failure(
    mock_connect: MagicMock, mock_sleep: MagicMock
) -> None:
    """A transient SQLSTATE failure should be retried once before succeeding."""
    mock_conn = MagicMock()
    mock_connect.side_effect = [_pyodbc_error("08S01"), mock_conn]

    with get_connection() as conn:
        assert conn is mock_conn

    assert mock_connect.call_count == 2
    mock_sleep.assert_called_once()


@patch("app.db.mssql.time.sleep")
@patch("app.db.mssql.pyodbc.connect")
def test_get_connection_raises_database_connection_error_after_max_attempts(
    mock_connect: MagicMock, mock_sleep: MagicMock
) -> None:
    """Persistent transient failures should raise DatabaseConnectionError, not the raw pyodbc error."""
    mock_connect.side_effect = _pyodbc_error("08S01")

    with pytest.raises(DatabaseConnectionError):
        with get_connection():
            pass

    assert mock_connect.call_count == 2


@patch("app.db.mssql.pyodbc.connect")
def test_get_connection_does_not_retry_non_transient_failure(mock_connect: MagicMock) -> None:
    """A non-transient error (e.g. bad login) should fail fast without retrying."""
    mock_connect.side_effect = _pyodbc_error("28000")

    with pytest.raises(DatabaseConnectionError):
        with get_connection():
            pass

    assert mock_connect.call_count == 1


@patch("app.db.mssql.pyodbc.connect")
def test_get_connection_closes_connection_even_if_caller_raises(mock_connect: MagicMock) -> None:
    """The connection must still be closed if the caller's code raises inside the with-block."""
    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn

    with pytest.raises(ValueError, match="boom"):
        with get_connection():
            raise ValueError("boom")

    mock_conn.close.assert_called_once()
