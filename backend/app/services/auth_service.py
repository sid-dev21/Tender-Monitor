"""Authentication business logic: registration and credential verification."""

from __future__ import annotations

from app.core.security import hash_password, verify_password
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
