
import os
import sys

try:
    import pyodbc
except ImportError:
    sys.exit("pyodbc is not installed. Run:  pip install pyodbc")

CONN = os.environ.get("APP_DB_CONN")
if not CONN:
    sys.exit("APP_DB_CONN is not set. Set it to your ODBC connection string first.")

print("Installed ODBC drivers:", pyodbc.drivers())
print("-" * 60)

try:
    with pyodbc.connect(CONN, timeout=5) as conn:
        cur = conn.cursor()

        # 1) Basic connection + identity
        cur.execute("SELECT DB_NAME(), SUSER_SNAME();")
        db, login = cur.fetchone() # type: ignore
        print(f"Connected OK.  Database = {db}   Login = {login}")

        # 2) Can we EXECUTE a function through the granted permissions?
        cur.execute("SELECT * FROM dbo.ufn_GetDueReports();")
        rows = cur.fetchall()
        print(f"ufn_GetDueReports() returned {len(rows)} due report(s).")

        # 3) Security check: direct table access MUST be denied for app_login.
        try:
            cur.execute("SELECT TOP 1 * FROM dbo.Users;")
            cur.fetchall()
            print("WARNING: direct SELECT on dbo.Users SUCCEEDED - the DENY grants "
                  "are not applied. Re-check file 03 (roles & grants).")
        except pyodbc.Error:
            print("Good: direct table access is DENIED (security model is working).")

    print("-" * 60)
    print("RESULT: the backend can reach the database through stored procedures. ✔")

except pyodbc.Error as e:
    print("-" * 60)
    print("CONNECTION FAILED:", e)
    print("Check: driver name in the string, SERVER host, UID/PWD, and that "
          "SQL Server allows SQL authentication + TCP/IP.")
    sys.exit(1)