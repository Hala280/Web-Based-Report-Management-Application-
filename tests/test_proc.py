"""Tests for app.db.proc.

Unit tests (mocked pyodbc cursor, no real DB) form the bulk of this file.
One clearly-marked INTEGRATION test at the bottom calls the real
dbo.ufn_GetDueReports() function and is skipped unless the caller explicitly
opts in — see that test's docstring for why APP_DB_CONN alone isn't used as
the skip signal.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from app.db.proc import call_proc, call_proc_scalar, query_function


def _patched_connection(cursor: MagicMock):
    """Patch app.db.proc.get_connection to yield a connection backed by `cursor`."""
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = cursor
    mock_ctx = MagicMock()
    mock_ctx.__enter__.return_value = mock_conn
    mock_ctx.__exit__.return_value = False
    return patch("app.db.proc.get_connection", return_value=mock_ctx), mock_conn


def test_call_proc_returns_rows_as_dicts() -> None:
    """call_proc should map cursor rows to a list of column-name -> value dicts."""
    cursor = MagicMock()
    cursor.description = [("Id",), ("Name",)]
    cursor.fetchall.return_value = [(1, "Alice"), (2, "Bob")]
    patcher, _ = _patched_connection(cursor)

    with patcher:
        rows = call_proc("dbo.usp_GetUsers")

    assert rows == [{"Id": 1, "Name": "Alice"}, {"Id": 2, "Name": "Bob"}]


def test_call_proc_builds_named_exec_and_binds_values_positionally() -> None:
    """Parameters must be bound via ? placeholders, never concatenated into the SQL text."""
    cursor = MagicMock()
    cursor.description = [("NewUserId",)]
    cursor.fetchall.return_value = [(42,)]
    patcher, _ = _patched_connection(cursor)

    with patcher:
        call_proc("dbo.usp_CreateUser", {"Username": "alice", "Email": "alice@example.com"})

    executed_sql, executed_params = cursor.execute.call_args[0]
    assert executed_sql == "EXEC dbo.usp_CreateUser @Username = ?, @Email = ?"
    assert executed_params == ["alice", "alice@example.com"]
    assert "alice" not in executed_sql
    assert "alice@example.com" not in executed_sql


def test_call_proc_with_no_params_builds_plain_exec() -> None:
    """A proc with no params should build a plain EXEC with an empty parameter list."""
    cursor = MagicMock()
    cursor.description = [("Id",)]
    cursor.fetchall.return_value = [(1,)]
    patcher, _ = _patched_connection(cursor)

    with patcher:
        call_proc("dbo.usp_GetUsers")

    executed_sql, executed_params = cursor.execute.call_args[0]
    assert executed_sql == "EXEC dbo.usp_GetUsers"
    assert executed_params == []


def test_call_proc_commits_after_execution() -> None:
    """call_proc must commit the transaction so writes performed by the proc persist."""
    cursor = MagicMock()
    cursor.description = [("NewUserId",)]
    cursor.fetchall.return_value = [(42,)]
    patcher, mock_conn = _patched_connection(cursor)

    with patcher:
        call_proc("dbo.usp_CreateUser", {"Username": "alice"})

    mock_conn.commit.assert_called_once()


def test_call_proc_scalar_returns_first_column_of_first_row() -> None:
    """call_proc_scalar should return only the first column of the first row."""
    cursor = MagicMock()
    cursor.description = [("NewUserId",), ("Extra",)]
    cursor.fetchall.return_value = [(42, "ignored")]
    patcher, _ = _patched_connection(cursor)

    with patcher:
        result = call_proc_scalar("dbo.usp_CreateUser", {"Username": "alice"})

    assert result == 42


def test_call_proc_scalar_returns_none_when_no_rows() -> None:
    """call_proc_scalar should return None when the proc returns no rows."""
    cursor = MagicMock()
    cursor.description = [("NewUserId",)]
    cursor.fetchall.return_value = []
    patcher, _ = _patched_connection(cursor)

    with patcher:
        result = call_proc_scalar("dbo.usp_CreateUser", {"Username": "alice"})

    assert result is None


def test_query_function_executes_parameterized_select_and_returns_rows() -> None:
    """query_function should execute the given SQL text with bound params and return dict rows."""
    cursor = MagicMock()
    cursor.description = [("ReportId",), ("DueDate",)]
    cursor.fetchall.return_value = [(1, "2026-07-01")]
    patcher, _ = _patched_connection(cursor)

    with patcher:
        rows = query_function(
            "SELECT * FROM dbo.ufn_GetDueReports(?)", {"AsOfDate": "2026-07-12"}
        )

    executed_sql, executed_params = cursor.execute.call_args[0]
    assert executed_sql == "SELECT * FROM dbo.ufn_GetDueReports(?)"
    assert executed_params == ["2026-07-12"]
    assert rows == [{"ReportId": 1, "DueDate": "2026-07-01"}]


def test_query_function_with_no_params() -> None:
    """query_function should execute with an empty parameter list when params is omitted."""
    cursor = MagicMock()
    cursor.description = [("ReportId",)]
    cursor.fetchall.return_value = [(1,)]
    patcher, _ = _patched_connection(cursor)

    with patcher:
        query_function("SELECT * FROM dbo.ufn_GetDueReports()")

    executed_sql, executed_params = cursor.execute.call_args[0]
    assert executed_sql == "SELECT * FROM dbo.ufn_GetDueReports()"
    assert executed_params == []


def test_call_proc_passes_varbinary_bytes_untouched() -> None:
    """VARBINARY columns (e.g. encrypted secrets) must pass through as raw bytes, undecoded."""
    cursor = MagicMock()
    cursor.description = [("Secret",)]
    secret_bytes = b"\x00\x01\xffsecret"
    cursor.fetchall.return_value = [(secret_bytes,)]
    patcher, _ = _patched_connection(cursor)

    with patcher:
        rows = call_proc("dbo.usp_GetSecret")

    assert rows[0]["Secret"] == secret_bytes
    assert isinstance(rows[0]["Secret"], bytes)


def test_call_proc_rejects_unsafe_proc_name() -> None:
    """An unsafe proc name (e.g. containing a SQL injection payload) must be rejected."""
    with pytest.raises(ValueError):
        call_proc("dbo.usp_Foo; DROP TABLE Users; --")


def test_call_proc_rejects_unsafe_param_name() -> None:
    """An unsafe parameter name must be rejected before it reaches SQL text."""
    with pytest.raises(ValueError):
        call_proc("dbo.usp_Foo", {"Bad Name; --": "x"})


@pytest.mark.skipif(
    os.environ.get("RUN_DB_INTEGRATION_TESTS") != "1",
    reason=(
        "Integration test requires a real ReportManagementDB reachable via "
        "APP_DB_CONN. The unit-test suite always provides a placeholder "
        "APP_DB_CONN (see tests/conftest.py) so import-time settings "
        "resolution works, meaning presence of that var alone cannot signal "
        "a real database. Set RUN_DB_INTEGRATION_TESTS=1 with a real "
        "APP_DB_CONN to opt in."
    ),
)
def test_integration_query_function_ufn_get_due_reports() -> None:
    """INTEGRATION: calls dbo.ufn_GetDueReports() against a real database."""
    rows = query_function("SELECT * FROM dbo.ufn_GetDueReports()")
    assert isinstance(rows, list)
