"""POST /auth/login."""

from fastapi import APIRouter

from app.schemas.user import LoginRequest, TokenResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    """Authenticate a username/password pair and return a JWT access token."""
    token = auth_service.authenticate(payload.username, payload.password)
    return TokenResponse(access_token=token)
