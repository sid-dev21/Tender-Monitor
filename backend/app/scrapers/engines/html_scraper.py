"""HTMLScraper — generic engine for sites whose tenders live in the page DOM."""

from __future__ import annotations

from typing import ClassVar

from app.models.enums import ContentType, Language, ScrapeTier
from app.models.site_config import SiteConfig
from app.models.tender import Tender
from app.scrapers.engines.base import BaseScraperEngine
from app.scrapers.extract import html_extractor


class HTMLScraper(BaseScraperEngine):
    content_type: ClassVar[ContentType] = ContentType.HTML

    async def _collect(
        self, site: SiteConfig
    ) -> tuple[list[Tender], ScrapeTier | None, list[str]]:
        errors: list[str] = []
        result = await self.router.fetch(site.base_url, site=site)
        tier = result.tier_used

        tenders: list[Tender] = []
        if not result.ok:
            errors.append(f"fetch_failed_status_{result.status_code}")
        else:
            language = Language.from_locale(site.locale)
            candidates = html_extractor.extract(
                result.html, site.extraction_rules, language, base_url=result.final_url
            )
            for candidate in candidates:
                tender = self._to_tender(candidate, site, tier)
                if tender is not None:
                    tenders.append(tender)

        return tenders, tier, errors
