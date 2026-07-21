"""PDFScraper — generic engine for sites that link to tender PDFs.

Fetches the landing page, discovers PDF document URLs (by selector, regex pattern,
or the default '.pdf' selector), streams each in-memory, and extracts. Scanned PDFs
are stored as needs_review (via document-URL reference) for the AI extractor later.
"""

from __future__ import annotations

import re
from typing import ClassVar
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from app.core.config import get_settings
from app.core.logging import logger
from app.models.enums import ContentType, Language, ScrapeTier
from app.models.site_config import SiteConfig
from app.models.tender import Tender
from app.scrapers.engines.base import BaseScraperEngine
from app.scrapers.extract import pdf_extractor


class PDFScraper(BaseScraperEngine):
    content_type: ClassVar[ContentType] = ContentType.PDF

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
            pdf_urls = self._find_pdf_urls(result.html, site)

            # Cap the batch: some portals link hundreds of documents.
            max_pdfs = get_settings().max_pdfs_per_run
            if len(pdf_urls) > max_pdfs:
                errors.append(f"pdf_limit_reached:{len(pdf_urls)}_found_{max_pdfs}_fetched")
                logger.warning(
                    "Site {} links {} PDFs; fetching only the first {}.",
                    site.base_url,
                    len(pdf_urls),
                    max_pdfs,
                )
                pdf_urls = pdf_urls[:max_pdfs]

            language = Language.from_locale(site.locale)
            timeout = httpx.Timeout(60.0)
            async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
                for url in pdf_urls:
                    try:
                        content = await pdf_extractor.stream_to_bytes(url, client)
                        if not pdf_extractor.looks_like_pdf(content):
                            errors.append(f"not_pdf:{url}")
                            continue
                        candidate = pdf_extractor.extract(content, language)
                        candidate.document_url = url
                        tender = self._to_tender(candidate, site, tier)
                        if tender is not None:
                            tenders.append(tender)
                    except Exception as exc:  # noqa: BLE001 - one bad PDF must not kill the run
                        errors.append(f"pdf_error:{url}:{exc}")

        return tenders, tier, errors

    def _find_pdf_urls(self, html: str, site: SiteConfig) -> list[str]:
        """Discover PDF document URLs from the landing page, resolved to absolute."""
        soup = BeautifulSoup(html, "lxml")
        rules = site.extraction_rules
        hrefs: list[str] = []

        if rules.pdf_link_selector:
            hrefs = [a.get("href", "") for a in soup.select(rules.pdf_link_selector)]
        elif rules.pdf_url_pattern:
            pattern = re.compile(rules.pdf_url_pattern)
            hrefs = [
                a.get("href", "")
                for a in soup.find_all("a", href=True)
                if pattern.search(a["href"])
            ]
        else:
            hrefs = [a.get("href", "") for a in soup.select(site.effective_pdf_link_selector())]

        # Resolve relative URLs and de-duplicate, preserving order.
        seen: set[str] = set()
        urls: list[str] = []
        for href in hrefs:
            if not href:
                continue
            absolute = urljoin(site.base_url, href)
            if absolute not in seen:
                seen.add(absolute)
                urls.append(absolute)
        return urls
