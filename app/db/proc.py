"""Stored-procedure and function calling primitives for ReportManagementDB.

This is the ONLY place in the app that builds SQL text. Values are always
passed as bound parameters — never string-interpolated. ODBC has no native
named-parameter syntax, so stored procedure and parameter *names* (never
values) are validated against a strict identifier allowlist before being
placed into the SQL text.
"""

import re
from typing import Any

from app.db.mssql import get_connection

_IDENTIFIER = r"[A-Za-z_][A-Za-z0-9_]*"
_PROC_NAME_RE = re.compile(rf"^({_IDENTIFIER}\.)?{_IDENTIFIER}$")
_PARAM_NAME_RE = re.compile(rf"^{_IDENTIFIER}$")


def _validate_proc_name(name: str) -> None:
    """Ensure a stored procedure/function name is a safe SQL identifier."""
    if not _PROC_NAME_RE.match(name):
        raise ValueError(f"Invalid stored procedure/function name: {name!r}")


def _validate_param_name(param: str) -> None:
    """Ensure a parameter name is a safe SQL identifier."""
    if not _PARAM_NAME_RE.match(param):
        raise ValueError(f"Invalid parameter name: {param!r}")


def _rows_to_dicts(cursor: Any) -> list[dict[str, Any]]:
    """Convert the cursor's current result set to a list of column->value dicts.

    Values (including VARBINARY columns, returned by pyodbc as bytes) are
    passed through untouched — no decoding happens here.
    """
    if cursor.description is None:
        return []
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def _build_exec_sql(name: str, params: dict[str, Any] | None) -> tuple[str, list[Any]]:
    """Build a parameterized EXEC statement: EXEC name @p1 = ?, @p2 = ? ..."""
    _validate_proc_name(name)
    params = params or {}
    for key in params:
        _validate_param_name(key)

    if not params:
        return f"EXEC {name}", []

    assignments = ", ".join(f"@{key} = ?" for key in params)
    return f"EXEC {name} {assignments}", list(params.values())


def call_proc(name: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Execute a stored procedure by name with named parameters, returning rows as dicts."""
    sql, values = _build_exec_sql(name, params)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, values)
        rows = _rows_to_dicts(cursor)
        conn.commit()
        return rows


def call_proc_scalar(name: str, params: dict[str, Any] | None = None) -> Any:
    """Execute a stored procedure and return the first column of its first row (or None)."""
    rows = call_proc(name, params)
    if not rows:
        return None
    return next(iter(rows[0].values()))


def query_function(sql_select: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Execute a parameterized SELECT against a table-valued function, returning rows as dicts.

    `sql_select` must already contain `?` placeholders for any parameters
    (e.g. "SELECT * FROM dbo.ufn_GetDueReports(?)"). Values are always bound,
    never string-interpolated.
    """
    values = list(params.values()) if params else []
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql_select, values)
        return _rows_to_dicts(cursor)
