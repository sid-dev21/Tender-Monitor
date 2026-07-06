"""Phase 1 — User repository & unique email index against a real MongoDB."""

from __future__ import annotations

import pytest
from pymongo.errors import DuplicateKeyError

from app.models.user import User
from app.repositories.user_repo import UserRepo


async def test_insert_and_find_by_email(db) -> None:  # noqa: ANN001
    repo = UserRepo(db)
    await repo.insert(User(email="sidoine@example.com", hashed_password="argon2$hash"))

    found = await repo.find_by_email("sidoine@example.com")
    assert found is not None
    assert found.email == "sidoine@example.com"
    assert found.is_active is True
    assert found.id is not None


async def test_duplicate_email_rejected(db) -> None:  # noqa: ANN001
    repo = UserRepo(db)
    await repo.insert(User(email="dup@example.com", hashed_password="h1"))

    with pytest.raises(DuplicateKeyError):
        await repo.insert(User(email="dup@example.com", hashed_password="h2"))
