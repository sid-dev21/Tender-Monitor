"""BaseScraperEngine — the contract both generic engines implement.

Both engines are driven entirely by a SiteConfig document. Shared logic lives here:
turning a TenderCandidate into a Tender (with a dedup-safe reference) and upserting
with deduplication. Subclasses implement scrape() for their content type.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar

from app.models.base import utcnow
from app.models.enums import ContentType, ScrapeTier
from app.models.scraper_run import ScraperRun
from app.models.site_config import SiteConfig
from app.models.tender import Tender
from app.repositories.run_repo import ScraperRunRepo
from app.repositories.tender_repo import TenderRepo
from app.scrapers.extract.candidate import TenderCandidate
from app.scrapers.fetch.router import TierRouter


@dataclass
class ScrapeResult:
    tenders: list[Tender] = field(default_factory=list)
    run: ScraperRun | None = None
    new_count: int = 0


class BaseScraperEngine(ABC):
    content_type: ClassVar[ContentType]

    def __init__(
        self, router: TierRouter, tender_repo: TenderRepo, run_repo: ScraperRunRepo
    ) -> None:
        self.router = router
        self.tenders = tender_repo
        self.runs = run_repo

    @abstractmethod
    async def _collect(
        self, site: SiteConfig
    ) -> tuple[list[Tender], ScrapeTier | None, list[str]]:
        """Fetch + extract + build tenders (no persistence). Returns (tenders, tier, errors)."""

    async def scrape(self, site: SiteConfig) -> ScrapeResult:
        """Fetch, extract, and persist tenders with deduplication + a run record."""
        tenders, tier, errors = await self._collect(site)
        stored, new_count = await self._save(tenders)
        run = await self._finish_run(site, tier, len(stored), errors)
        return ScrapeResult(tenders=stored, run=run, new_count=new_count)

    async def preview(self, site: SiteConfig) -> ScrapeResult:
        """Dry-run: fetch + extract, but persist nothing (for /sites/{id}/test)."""
        tenders, tier, _errors = await self._collect(site)
        return ScrapeResult(tenders=tenders, run=None, new_count=0)

    # --- shared helpers ---
    def _to_tender(
        self, c: TenderCandidate, site: SiteConfig, tier: ScrapeTier | None
    ) -> Tender | None:
        """Build a Tender from a candidate. Needs a dedup reference to be storable.

        Falls back to the document URL as the reference (e.g. scanned ARCOP PDFs have
        no parsed reference but a unique /telechargement/{id} URL), so they still
        persist as needs_review for the AI extractor to enrich later.
        """
        reference = c.reference_number or c.document_url
        if not reference:
            return None  # nothing to dedup on; skip
        return Tender(
            title=c.title or reference,
            reference_number=reference,
            publication_date=c.publication_date,
            deadline=c.deadline,
            contracting_authority=c.contracting_authority,
            sector=c.sector,
            estimated_budget=c.estimated_budget,
            currency=c.currency,
            document_url=c.document_url,
            source_site_id=site.id,
            extraction_type=self.content_type,
            scrape_tier_used=tier,
            raw_text=c.raw_text,
            status=c.status(),
        )

    async def _save(self, tenders: list[Tender]) -> tuple[list[Tender], int]:
        """Upsert tenders by (reference, site); return (stored, new_count)."""
        stored: list[Tender] = []
        new_count = 0
        for tender in tenders:
            saved, created = await self.tenders.upsert_by_reference(tender)
            stored.append(saved)
            new_count += int(created)
        return stored, new_count

    async def _finish_run(
        self,
        site: SiteConfig,
        tier: ScrapeTier | None,
        found: int,
        errors: list[str],
    ) -> ScraperRun:
        run = ScraperRun(
            site_id=site.id,
            end_time=utcnow(),
            tenders_found=found,
            tier_used=tier,
            errors=errors,
        )
        return await self.runs.insert(run)
