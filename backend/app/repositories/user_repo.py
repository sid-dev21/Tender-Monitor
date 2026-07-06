"""Repository for User documents."""

from __future__ import annotations

from typing import ClassVar

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepo(BaseRepository[User]):
    collection_name: ClassVar[str] = "users"
    model = User

    async def find_by_email(self, email: str) -> User | None:
        """Look up a user by email (email is unique — see init_indexes.py)."""
        return await self.find_one({"email": email})
