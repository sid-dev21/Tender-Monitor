"""Authentication business logic: registration and credential verification."""

from __future__ import annotations

from app.core.security import (
    create_reset_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repo import UserRepo


class EmailAlreadyRegistered(Exception):
    pass


class AuthService:
    def __init__(self, users: UserRepo) -> None:
        self._users = users

    async def register(self, email: str, password: str) -> User:
        if await self._users.find_by_email(email) is not None:
            raise EmailAlreadyRegistered(email)
        user = User(email=email, hashed_password=hash_password(password))
        return await self._users.insert(user)

    async def authenticate(self, email: str, password: str) -> User | None:
        user = await self._users.find_by_email(email)
        if user is None or not user.is_active:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    async def request_password_reset(self, email: str) -> str | None:
        """Return a short-lived reset token if an active account exists, else None.

        The caller (API) must NOT leak which of these happened — it always
        returns 200 to prevent account enumeration.
        """
        user = await self._users.find_by_email(email)
        if user is None or not user.is_active:
            return None
        return create_reset_token(str(user.id))

    async def reset_password(self, token: str, new_password: str) -> bool:
        """Set a new password from a valid reset token. False if token invalid/stale."""
        subject = decode_token(token, expected_type="reset")
        if subject is None:
            return False
        updated = await self._users.update_by_id(
            subject, {"hashed_password": hash_password(new_password)}
        )
        return updated is not None
