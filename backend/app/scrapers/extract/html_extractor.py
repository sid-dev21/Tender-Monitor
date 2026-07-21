"""HTML extractor: config-driven CSS selectors + field-parser fallback.

Driven entirely by SiteConfig.extraction_rules. Selectors pull what they can; the
multi-language field parser fills the gaps (when regex_fallback_enabled). If no
list_selector is set, the whole page is treated as a single tender block.
"""

from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from app.models.enums import Language
from app.models.site_config import ExtractionRules
from app.scrapers.extract.candidate import TenderCandidate
from app.scrapers.extract.field_parser import parse_fields


def _sel_text(block: Tag, selector: str | None) -> str | None:
    if not selector:
        return None
    el = block.select_one(selector)
    if el is None:
        return None
    text = el.get_text(" ", strip=True)
    return text or None


# Selectors tried (in order) to auto-detect repeated tender blocks when the site
# config gives no list_selector. The first that yields >= 2 tender-looking blocks wins.
_FALLBACK_LIST_SELECTORS = (
    "article",
    "[class*=tender]",
    "[class*=avis]",
    "[class*=offre]",
    "[class*=appel]",
    "[class*=marche]",
    "li",
)

# Vocabulary hint that a block is about procurement.
_TENDER_HINTS = (
    "appel d",
    "avis",
    "marche",
    "tender",
    "ausschreibung",
    "vergabe",
    "date limite",
    "deadline",
)

# A HARD signal that a block is an actual notice, not a nav/menu item: a reference
# number, a date, a year, or a currency amount. Menu links ("Écrivez-nous",
# "Marchés publics & PME") have the vocabulary but never these.
_SIGNAL_RE = re.compile(
    r"n[°ºo]\s*[:\-]?\s*[A-Za-z0-9]"          # N° 2026-101
    r"|\d{1,2}[./-]\d{1,2}[./-]\d{4}"          # 12/03/2026
    r"|\d{4}-\d{2}-\d{2}"                      # 2026-03-12
    r"|\b20\d{2}\b"                            # a year
    r"|fcfa|xof|eur\b|€|gbp\b|£|usd\b",        # a currency
    re.IGNORECASE,
)


def _looks_like_tender(text: str) -> bool:
    """Procurement vocabulary AND a hard signal (ref / date / year / amount)."""
    low = text.lower()
    return any(h in low for h in _TENDER_HINTS) and bool(_SIGNAL_RE.search(low))


def _is_noise(candidate: TenderCandidate) -> bool:
    """A real tender yields at least one of: reference, deadline, or budget."""
    return (
        candidate.reference_number is None
        and candidate.deadline is None
        and candidate.estimated_budget is None
    )


def _auto_blocks(soup: BeautifulSoup) -> list[Tag] | None:
    """Find repeated tender blocks without a configured selector."""
    for selector in _FALLBACK_LIST_SELECTORS:
        candidates = [b for b in soup.select(selector) if isinstance(b, Tag)]
        good = [b for b in candidates if _looks_like_tender(b.get_text(" ", strip=True))]
        if len(good) >= 2:
            return good
    return None


def _block_source_url(block: Tag, base_url: str | None) -> str | None:
    """Link for this tender: the block's own anchor if any, else the page URL."""
    if base_url is None:
        return None
    anchor = block.find("a", href=True)
    if anchor is not None:
        return urljoin(base_url, str(anchor["href"]))
    return base_url


def _fallback_title(block: Tag, raw_text: str) -> str | None:
    for tag in ("h1", "h2", "h3"):
        el = block.find(tag)
        if el is not None:
            text = el.get_text(" ", strip=True)
            if text:
                return text
    first_line = raw_text.strip().splitlines()[0] if raw_text.strip() else ""
    return first_line[:200] or None


def extract(
    html: str,
    rules: ExtractionRules,
    language: Language = Language.FRENCH,
    base_url: str | None = None,
) -> list[TenderCandidate]:
    """Extract tender candidates from an HTML page using the site's rules.

    `base_url` (the page's URL) is used to build each tender's document_url, so
    the UI can always link back to the source.
    """
    soup = BeautifulSoup(html, "lxml")

    whole_page_fallback = False
    if rules.list_selector:
        blocks: list[Tag] = soup.select(rules.list_selector)
    else:
        # No configured selector: try to auto-detect repeated tender blocks;
        # otherwise treat the whole page as a single block.
        auto = _auto_blocks(soup)
        if auto is not None:
            blocks = auto
        else:
            body = soup.body or soup
            blocks = [body] if isinstance(body, Tag) else []
            whole_page_fallback = True

    candidates: list[TenderCandidate] = []
    for block in blocks:
        # Newline separator keeps each element on its own line, so "label: value"
        # captures (authority, deadline) don't bleed into the next field.
        raw_text = block.get_text("\n", strip=True)
        c = TenderCandidate(
            title=_sel_text(block, rules.title_selector),
            reference_number=_sel_text(block, rules.reference_selector),
            contracting_authority=_sel_text(block, rules.authority_selector),
            document_url=_block_source_url(block, base_url),
            raw_text=raw_text,
        )

        if rules.regex_fallback_enabled:
            parse_fields(raw_text, language, into=c)

        if not c.title:
            c.title = _fallback_title(block, raw_text)

        # Reject navigation/menu noise: a real tender has a reference, a deadline,
        # or a budget. Without any of those, it is not a tender notice.
        if _is_noise(c):
            continue

        # Parsing a whole listing page as one block yields plausible-looking junk
        # (a stray date, a stray amount). Demand stronger evidence there.
        if whole_page_fallback and c.field_count() < 2:
            continue

        # Skip empty blocks (a list_selector that matched layout noise).
        if c.title or c.reference_number:
            candidates.append(c)

    return candidates
