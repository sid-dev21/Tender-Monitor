"""Repository for SiteConfig documents."""

from __future__ import annotations

from typing import ClassVar

from bson import ObjectId

from app.models.site_config import SiteConfig
from app.repositories.base import BaseRepository


class SiteConfigRepo(BaseRepository[SiteConfig]):
    collection_name: ClassVar[str] = "site_configs"
    model = SiteConfig

    async def find_by_user(
        self, user_id: str | ObjectId, *, active_only: bool = False
    ) -> list[SiteConfig]:
        """All sites owned by a user (optionally only active ones)."""
        flt: dict = {"created_by_user_id": self._oid(user_id)}
        if active_only:
            flt["is_active"] = True
        return await self.find(flt, sort=[("created_at", -1)])

    async def find_all_active(self) -> list[SiteConfig]:
        """Every active site across all users — the scheduler's scrape worklist."""
        return await self.find({"is_active": True})
