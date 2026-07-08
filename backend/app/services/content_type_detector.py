"""Auto-detect whether a source URL is best handled by the HTML or PDF engine.

Best-effort heuristic (the user can always override content_type explicitly):
  - If the URL itself returns PDF bytes -> PDF.
  - Else fetch the page and compare PDF-like links to total links. ARCOP-style
    '/telechargement/{id}' and '/download' links count as PDF links (real ARCOP
    docs have no .pdf suffix).
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from app.models.enums import ContentType
from app.scrapers.extract.pdf_extractor import looks_like_pdf
from app.scrapers.fetch.tier1_httpx import fetch_tier1

_PDF_LINK_RE = re.compile(r"\.pdf($|\?)|/telechargement/|/download", re.IGNORECASE)
_PDF_DOMINANCE = 0.3  # >=30% of links look like documents => PDF site


async def detect_content_type(url: str) -> ContentType:
    result = await fetch_tier1(url)

    # The URL is itself a PDF document.
    if looks_like_pdf(result.html.encode("latin-1", errors="ignore")[:1024]):
        return ContentType.PDF
    if "application/pdf" in result.headers.get("content-type", ""):
        return ContentType.PDF

    soup = BeautifulSoup(result.html, "lxml")
    links = [a.get("href", "") for a in soup.find_all("a", href=True)]
    if not links:
        return ContentType.HTML
    pdf_like = sum(1 for href in links if _PDF_LINK_RE.search(href))
    ratio = pdf_like / len(links)
    return ContentType.PDF if ratio >= _PDF_DOMINANCE else ContentType.HTML
