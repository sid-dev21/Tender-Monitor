"""Scrape orchestration: wire repositories + router + engine registry for a site.

run_scrape(site_id) is the single entry point the API and scheduler call. It loads
the SiteConfig, picks the engine by content_type, runs it, and returns the result
(tenders + the ScraperRun audit record).
"""

from __future__ import annotations

from bson import ObjectId
from pymongo.asynchronous.database import AsyncDatabase

from app.repositories.rate_limit_repo import RateLimitStateRepo
from app.repositories.run_repo import ScraperRunRepo
from app.repositories.site_config_repo import SiteConfigRepo
from app.repositories.tender_repo import TenderRepo
from app.scrapers.engines.base import ScrapeResult
from app.scrapers.engines.registry import EngineRegistry
from app.scrapers.fetch.router import TierRouter


def build_registry(db: AsyncDatabase) -> EngineRegistry:
    """Assemble the engine registry with all repositories wired to `db`."""
    router = TierRouter(RateLimitStateRepo(db))
    return EngineRegistry(router, TenderRepo(db), ScraperRunRepo(db))


async def run_scrape(
    site_id: str | ObjectId, db: AsyncDatabase, *, dry_run: bool = False
) -> ScrapeResult:
    """Load a site, dispatch to its engine, run the scrape, return the result.

    dry_run=True previews extraction without persisting anything (for /sites/{id}/test).
    """
    site = await SiteConfigRepo(db).find_by_id(site_id)
    if site is None:
        raise ValueError(f"SiteConfig not found: {site_id}")
    engine = build_registry(db).engine_for(site.content_type)
    return await engine.preview(site) if dry_run else await engine.scrape(site)
