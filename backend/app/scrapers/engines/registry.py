"""EngineRegistry — maps a site's content_type to the engine that handles it.

This is the seam that makes the two-engine architecture work: content_type is data
on the SiteConfig, and the registry dispatches to the matching engine. Adding a site
never touches this file.
"""

from __future__ import annotations

from app.models.enums import ContentType
from app.repositories.run_repo import ScraperRunRepo
from app.repositories.tender_repo import TenderRepo
from app.scrapers.engines.base import BaseScraperEngine
from app.scrapers.engines.html_scraper import HTMLScraper
from app.scrapers.engines.pdf_scraper import PDFScraper
from app.scrapers.fetch.router import TierRouter


class EngineRegistry:
    def __init__(
        self, router: TierRouter, tender_repo: TenderRepo, run_repo: ScraperRunRepo
    ) -> None:
        self._engines: dict[ContentType, BaseScraperEngine] = {
            ContentType.HTML: HTMLScraper(router, tender_repo, run_repo),
            ContentType.PDF: PDFScraper(router, tender_repo, run_repo),
        }

    def engine_for(self, content_type: ContentType) -> BaseScraperEngine:
        return self._engines[content_type]
