"""Authentication endpoints: register, login, refresh."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pymongo.asynchronous.database import AsyncDatabase

from app.core.config import frontend_is_bundled, get_settings
from app.core.logging import logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.dependencies.deps import get_db
from app.repositories.user_repo import UserRepo
from app.schemas.auth_dto import (
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import AuthService, EmailAlreadyRegistered
from app.services.notifiers.email import send_password_reset

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _tokens(user_id: str) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncDatabase = Depends(get_db)) -> UserResponse:
    service = AuthService(UserRepo(db))
    try:
        user = await service.register(body.email, body.password)
    except EmailAlreadyRegistered as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        ) from exc
    return UserResponse.from_user(user)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncDatabase = Depends(get_db)) -> TokenResponse:
    service = AuthService(UserRepo(db))
    user = await service.authenticate(body.email, body.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    return _tokens(str(user.id))


def _frontend_origin(request: Request) -> str:
    """Where the reset link should point.

    When the SPA is served by this same app (single-origin deployment), the
    origin the browser just used IS the frontend — deriving it from the request
    keeps the emailed link valid behind a tunnel URL that changes on every
    restart, with nothing to reconfigure. FRONTEND_BASE_URL stays authoritative
    when set to something other than the default, for split deployments where
    the SPA lives elsewhere (Vercel).
    """
    if frontend_is_bundled():
        return str(request.base_url).rstrip("/")
    return get_settings().frontend_base_url


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(
    body: ForgotPasswordRequest, request: Request, db: AsyncDatabase = Depends(get_db)
) -> dict[str, bool]:
    """Email a reset link if the account exists.

    Always returns 202 with the same body regardless of whether the email is
    registered — this prevents account-enumeration. SMTP failures are logged but
    never surfaced (again, no enumeration and resilience).
    """
    service = AuthService(UserRepo(db))
    token = await service.request_password_reset(body.email)
    if token is not None:
        reset_url = f"{_frontend_origin(request)}/reset-password?token={token}"
        try:
            await send_password_reset(body.email, reset_url)
        except Exception as exc:  # noqa: BLE001 - never leak SMTP state to the client
            logger.warning("Password-reset email failed for {}: {}", body.email, exc)
    return {"ok": True}


@router.post("/reset-password", response_model=TokenResponse)
async def reset_password(
    body: ResetPasswordRequest, db: AsyncDatabase = Depends(get_db)
) -> TokenResponse:
    """Set a new password from a valid reset token and log the user straight in."""
    service = AuthService(UserRepo(db))
    subject = decode_token(body.token, expected_type="reset")
    ok = await service.reset_password(body.token, body.new_password)
    if not ok or subject is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )
    return _tokens(subject)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncDatabase = Depends(get_db)) -> TokenResponse:
    subject = decode_token(body.refresh_token, expected_type="refresh")
    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    user = await UserRepo(db).find_by_id(subject)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    return _tokens(subject)
