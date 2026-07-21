"""PDF extractor: in-memory only, NEVER writes to disk.

Streams a PDF into a BytesIO, extracts text with pdfplumber, and runs the field
parser. PDF detection uses the %PDF- magic bytes (real ARCOP docs are served as
Content-Type 'application/download' with no .pdf suffix, so content is the only
reliable signal).

Scanned/image PDFs (pdfplumber yields ~no text but pages have images) are DETECTED
and flagged is_scanned=True / needs_review — extraction of those is deferred to the
AI vision extractor (see ai roadmap). We never crash on them.
"""

from __future__ import annotations

import io

import httpx
import pdfplumber

from app.core.logging import logger
from app.models.enums import Language
from app.scrapers.extract.candidate import TenderCandidate
from app.scrapers.extract.field_parser import parse_fields

PDF_MAGIC = b"%PDF-"
MAX_PDF_BYTES = 25 * 1024 * 1024  # 25 MB safety cap
# Below this many extracted chars, with images present, we treat it as a scan.
_SCANNED_TEXT_THRESHOLD = 20


def looks_like_pdf(content: bytes) -> bool:
    """True if the bytes begin with the PDF magic number (allowing a small BOM/offset)."""
    return PDF_MAGIC in content[:1024]


async def stream_to_bytes(
    url: str, client: httpx.AsyncClient, *, max_bytes: int = MAX_PDF_BYTES
) -> bytes:
    """Stream a URL into memory (BytesIO), enforcing a size cap. Never writes to disk."""
    buffer = io.BytesIO()
    async with client.stream("GET", url) as resp:
        resp.raise_for_status()
        async for chunk in resp.aiter_bytes():
            buffer.write(chunk)
            if buffer.tell() > max_bytes:
                raise ValueError(f"PDF exceeds {max_bytes} bytes: {url}")
    return buffer.getvalue()


def extract(pdf_bytes: bytes, language: Language = Language.FRENCH) -> TenderCandidate:
    """Extract a TenderCandidate from PDF bytes. Flags scans instead of failing."""
    text_parts: list[str] = []
    image_count = 0
    page_count = 0
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as doc:
        page_count = len(doc.pages)
        for page in doc.pages:
            page_text = page.extract_text() or ""
            text_parts.append(page_text)
            image_count += len(page.images)
    full_text = "\n".join(text_parts).strip()

    # No extractable text => nothing a regex parser can do. This covers scanned
    # image PDFs AND malformed/0-page documents. Either way it needs the vision
    # extractor (AI roadmap), so flag it rather than emit an empty tender.
    if len(full_text) < _SCANNED_TEXT_THRESHOLD:
        logger.info(
            "PDF has no extractable text (chars={}, images={}, pages={})",
            len(full_text),
            image_count,
            page_count,
        )
        return TenderCandidate(is_scanned=True, raw_text=full_text or None)

    return parse_fields(full_text, language)
