"""User account model."""

from __future__ import annotations

from pydantic import EmailStr, Field

from app.models.base import MongoModel


class User(MongoModel):
    """A registered user of Tender Monitor.

    Stored in the `users` collection. `email` is unique (enforced by an index in
    scripts/init_indexes.py). `hashed_password` holds an argon2 hash — never a
    plaintext password.
    """

    email: EmailStr
    hashed_password: str

    # Free-text company profile (sector, kind of projects sought, size...). Used as
    # context for LLM relevance scoring (services/relevance_scorer.py) on top of the
    # keyword filter — the semantic layer keyword matching alone cannot provide.
    company_profile: str | None = Field(default=None, max_length=2000)

    # Keywords the user monitors. Normalized (lowercase, accent-stripped) before
    # storage by the keyword service in Phase 8. Capped for sanity.
    keywords: list[str] = Field(default_factory=list, max_length=50)

    # Recipient addresses for email reports. Hard cap of 5, enforced HERE so no
    # API path can ever bypass it, and again at the API layer for a clean 422.
    notification_emails: list[EmailStr] = Field(default_factory=list, max_length=5)

    in_app_notifications_enabled: bool = True
    is_active: bool = True
