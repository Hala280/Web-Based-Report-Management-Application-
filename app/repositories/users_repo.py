"""Thin wrappers around the Phase 3 user/auth stored procedures.

Each function maps 1:1 to one allowed stored procedure and does nothing else
— no business logic, no hashing, no JWT handling (that belongs in
app/services). This is the only module that knows the parameter names of
these procs.

Proc contracts (verified against the real ReportManagementDB DDL):

    usp_GetUserForLogin(@Username)
        -> 0 or 1 row: UserId, Username, PasswordHash, Role, IsActive

    usp_User_Create(@Username, @PasswordHash, @Role)
        -> scalar NewUserId

    usp_User_Update(@UserId, @Username, @Role, @Status)
        @Status is 'active' | 'inactive' (translated here from the
        `is_active: bool | None` the service layer passes in). There is no
        @IsActive parameter. Untouched fields are passed as None; the proc
        is assumed to use COALESCE(@Param, existing_value) so a partial
        update doesn't require a prior read.

    usp_User_SetPassword(@UserId, @PasswordHash)

    usp_User_Delete(@UserId)
        Deactivates the user (sets Status='inactive') internally — takes
        no other parameters.

    usp_Log_Add(@Action, @UserId, @ReportId, @EntityType, @Status)
        There is no @Details parameter. Only @Action, @UserId, and
        @EntityType are used by this module (@ReportId and @Status are
        report-domain fields not applicable to user/auth audit events, so
        they're omitted from the EXEC call and rely on the proc's own
        defaults). @UserId is nullable — used for events with no
        authenticated actor (e.g. a failed login for an unknown username).
"""

from typing import Any

from app.db.proc import call_proc, call_proc_scalar


def get_user_for_login(username: str) -> dict[str, Any] | None:
    """Fetch the login row for a username, or None if no such user exists."""
    rows = call_proc("dbo.usp_GetUserForLogin", {"Username": username})
    return rows[0] if rows else None


def create_user(username: str, password_hash: str, role: str) -> int:
    """Create a user and return the new UserId."""
    new_id = call_proc_scalar(
        "dbo.usp_User_Create",
        {"Username": username, "PasswordHash": password_hash, "Role": role},
    )
    return int(new_id)


def update_user(
    user_id: int, username: str | None, role: str | None, is_active: bool | None
) -> None:
    """Update the fields of an existing user. None means "leave unchanged".

    `is_active` is translated to the proc's @Status ('active' | 'inactive')
    — there is no @IsActive parameter.
    """
    status = None if is_active is None else ("active" if is_active else "inactive")
    call_proc(
        "dbo.usp_User_Update",
        {"UserId": user_id, "Username": username, "Role": role, "Status": status},
    )


def set_password(user_id: int, password_hash: str) -> None:
    """Overwrite a user's stored password hash."""
    call_proc("dbo.usp_User_SetPassword", {"UserId": user_id, "PasswordHash": password_hash})


def delete_user(user_id: int) -> None:
    """Deactivate a user; the proc sets Status='inactive' internally."""
    call_proc("dbo.usp_User_Delete", {"UserId": user_id})


def add_log(user_id: int | None, action: str, entity_type: str | None = None) -> None:
    """Write an audit log entry. `entity_type` is the proc's @EntityType (e.g. 'user')."""
    call_proc(
        "dbo.usp_Log_Add",
        {"Action": action, "UserId": user_id, "EntityType": entity_type},
    )
