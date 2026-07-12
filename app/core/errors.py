"""Application-level exceptions and FastAPI exception handlers.

Handlers always return clean, generic JSON and never leak internals
(stack traces, DB error text, secrets) to the client.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.logging_config import get_logger

logger = get_logger(__name__)


class AppError(Exception):
    """Base class for application errors that map to an HTTP response."""

    status_code: int = 500
    public_message: str = "An unexpected error occurred."

    def __init__(self, message: str | None = None) -> None:
        if message:
            self.public_message = message
        super().__init__(self.public_message)


class NotFoundError(AppError):
    """Raised when a requested resource does not exist."""

    status_code = 404
    public_message = "The requested resource was not found."


class AuthError(AppError):
    """Raised for authentication failures.

    The message is always the generic default, regardless of what the
    caller passes in, so responses never reveal whether a specific
    username/email/account exists.
    """

    status_code = 401
    public_message = "Invalid credentials."

    def __init__(self, message: str | None = None) -> None:  # noqa: ARG002
        super().__init__(None)


class PermissionError(AppError):
    """Raised when an authenticated caller lacks permission for an action."""

    status_code = 403
    public_message = "You do not have permission to perform this action."


class ValidationError(AppError):
    """Raised for application-level validation failures."""

    status_code = 422
    public_message = "Invalid input."


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Map an AppError to a clean JSON response, logging the details server-side."""
    logger.warning(
        "AppError handled: %s status=%s path=%s",
        type(exc).__name__,
        exc.status_code,
        request.url.path,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"message": exc.public_message}},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler: log full details server-side, return a generic 500 to the client."""
    logger.error(
        "Unhandled exception on path=%s: %s",
        request.url.path,
        type(exc).__name__,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"error": {"message": "An unexpected error occurred."}},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register the AppError and catch-all exception handlers on the FastAPI app."""
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
