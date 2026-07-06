"""Repository for DomainRateLimitState documents."""

from __future__ import annotations

from typing import Any, ClassVar

from app.models.rate_limit import DomainRateLimitState
from app.repositories.base import BaseRepository


class RateLimitStateRepo(BaseRepository[DomainRateLimitState]):
    collection_name: ClassVar[str] = "domain_rate_limit_state"
    model = DomainRateLimitState

    async def find_by_domain(self, domain: str) -> DomainRateLimitState | None:
        return await self.find_one({"domain": domain})

    async def get_or_create(self, domain: str) -> DomainRateLimitState:
        """Return the domain's state, creating a default document if absent."""
        existing = await self.find_by_domain(domain)
        if existing is not None:
            return existing
        return await self.insert(DomainRateLimitState(domain=domain))

    async def apply(self, domain: str, update: dict[str, Any]) -> DomainRateLimitState | None:
        """Apply a raw Mongo update (e.g. $set/$inc) atomically, upserting by domain.

        Used by the rate limiter for race-free counter/backoff updates in Phase 4.
        """
        from pymongo import ReturnDocument

        doc = await self.collection.find_one_and_update(
            {"domain": domain}, update, upsert=True, return_document=ReturnDocument.AFTER
        )
        return self._to_model(doc)
