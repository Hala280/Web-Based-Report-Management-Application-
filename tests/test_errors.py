"""Unit tests for app.core.errors: AppError hierarchy and exception handlers."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.errors import (
    AppError,
    AuthError,
    NotFoundError,
)
from app.core.errors import PermissionError as AppPermissionError
from app.core.errors import ValidationError as AppValidationError
from app.core.errors import register_exception_handlers


def _build_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/not-found")
    def raise_not_found():
        raise NotFoundError("Report 123 not found.")

    @app.get("/auth-error")
    def raise_auth_error():
        raise AuthError("No user with email x@example.com exists.")

    @app.get("/permission-error")
    def raise_permission_error():
        raise AppPermissionError()

    @app.get("/validation-error")
    def raise_validation_error():
        raise AppValidationError("Bad field.")

    @app.get("/boom")
    def raise_unexpected():
        raise RuntimeError("db password is hunter2")

    return app


client = TestClient(_build_app(), raise_server_exceptions=False)


def test_not_found_error_returns_404_with_message() -> None:
    """NotFoundError should map to a 404 with its custom message."""
    resp = client.get("/not-found")
    assert resp.status_code == 404
    assert resp.json() == {"error": {"message": "Report 123 not found."}}


def test_auth_error_returns_401_generic_message_no_enumeration() -> None:
    """AuthError must always return the generic message, never the caller-supplied detail."""
    resp = client.get("/auth-error")
    assert resp.status_code == 401
    assert resp.json() == {"error": {"message": "Invalid credentials."}}
    assert "x@example.com" not in resp.text


def test_permission_error_returns_403_default_message() -> None:
    """PermissionError should map to a 403 with its default message."""
    resp = client.get("/permission-error")
    assert resp.status_code == 403
    assert resp.json() == {
        "error": {"message": "You do not have permission to perform this action."}
    }


def test_validation_error_returns_422_with_message() -> None:
    """ValidationError should map to a 422 with its custom message."""
    resp = client.get("/validation-error")
    assert resp.status_code == 422
    assert resp.json() == {"error": {"message": "Bad field."}}


def test_unhandled_exception_returns_500_generic_no_internals_leaked() -> None:
    """Unhandled exceptions must never leak internal details (e.g. secrets) to the client."""
    resp = client.get("/boom")
    assert resp.status_code == 500
    assert resp.json() == {"error": {"message": "An unexpected error occurred."}}
    assert "hunter2" not in resp.text


def test_app_error_default_status_code_is_500() -> None:
    """The AppError base class should default to a 500 status code."""
    assert AppError().status_code == 500
