"""Shared FastAPI dependencies: database handle and current-user resolution."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pymongo.asynchronous.database import AsyncDatabase

from app.core import db as db_module
from app.core.security import decode_token
from app.models.user import User
from app.repositories.user_repo import UserRepo

_bearer = HTTPBearer(auto_error=True)


def get_db() -> AsyncDatabase:
    """The active database. Overridable in tests via dependency_overrides."""
    return db_module.get_db()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncDatabase = Depends(get_db),
) -> User:
    """Resolve and return the authenticated user from a Bearer access token."""
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    subject = decode_token(credentials.credentials, expected_type="access")
    if subject is None:
        raise unauthorized
    user = await UserRepo(db).find_by_id(subject)
    if user is None or not user.is_active:
        raise unauthorized
    return user
