"""Authentication endpoints: register, login, refresh."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.asynchronous.database import AsyncDatabase

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.dependencies.deps import get_db
from app.repositories.user_repo import UserRepo
from app.schemas.auth_dto import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import AuthService, EmailAlreadyRegistered

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
