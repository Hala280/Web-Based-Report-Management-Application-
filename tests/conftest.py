"""Shared pytest fixtures.

Ensures required Settings env vars exist before any module is imported,
since several modules resolve settings (and therefore configure logging)
at import time.
"""

import os

os.environ.setdefault(
    "APP_DB_CONN",
    "Driver={ODBC Driver 17 for SQL Server};Server=x;Database=y;UID=u;PWD=p;",
)
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("JWT_EXPIRE_MINUTES", "60")
os.environ.setdefault("CRED_ENCRYPTION_KEY", "test-key")
os.environ.setdefault("LOG_LEVEL", "INFO")
