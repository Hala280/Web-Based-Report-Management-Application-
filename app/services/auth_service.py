"""Login authentication: verify credentials, issue a JWT, audit the attempt.

The JWT `sub` claim carries the numeric UserId (as a string) rather than the
username, since every downstream proc (usp_User_Update, usp_Log_Add, ...)
keys off UserId.
"""

from app.core.errors import AuthError
from app.core.security import create_access_token, verify_password
from app.repositories import users_repo

_LOGIN_FAILED = "LOGIN_FAILED"
_LOGIN_SUCCESS = "LOGIN_SUCCESS"
_ENTITY_TYPE_USER = "user"


def authenticate(username: str, password: str) -> str:
    """Verify a username/password pair and return a signed JWT access token.

    Raises AuthError — always the same generic "Invalid credentials."
    message — for an unknown username, a wrong password, or an inactive
    account, so the response never discloses which case occurred (no user
    enumeration).
    """
    user = users_repo.get_user_for_login(username)

    if user is None:
        users_repo.add_log(None, _LOGIN_FAILED, entity_type=_ENTITY_TYPE_USER)
        raise AuthError()

    if not user.get("IsActive", True):
        users_repo.add_log(user["UserId"], _LOGIN_FAILED, entity_type=_ENTITY_TYPE_USER)
        raise AuthError()

    if not verify_password(password, user["PasswordHash"]):
        users_repo.add_log(user["UserId"], _LOGIN_FAILED, entity_type=_ENTITY_TYPE_USER)
        raise AuthError()

    users_repo.add_log(user["UserId"], _LOGIN_SUCCESS, entity_type=_ENTITY_TYPE_USER)
    return create_access_token(subject=str(user["UserId"]), role=user["Role"])
