"""Repository for ScraperRun audit documents."""

from __future__ import annotations

from typing import ClassVar

from bson import ObjectId

from app.models.scraper_run import ScraperRun
from app.repositories.base import BaseRepository


class ScraperRunRepo(BaseRepository[ScraperRun]):
    collection_name: ClassVar[str] = "scraper_runs"
    model = ScraperRun

    async def recent_for_site(
        self, site_id: str | ObjectId, *, limit: int = 20
    ) -> list[ScraperRun]:
        return await self.find(
            {"site_id": self._oid(site_id)}, limit=limit, sort=[("start_time", -1)]
        )
