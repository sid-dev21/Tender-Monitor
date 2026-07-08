"""HTML extractor: config-driven CSS selectors + field-parser fallback.

Driven entirely by SiteConfig.extraction_rules. Selectors pull what they can; the
multi-language field parser fills the gaps (when regex_fallback_enabled). If no
list_selector is set, the whole page is treated as a single tender block.
"""

from __future__ import annotations

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
) -> list[TenderCandidate]:
    """Extract tender candidates from an HTML page using the site's rules."""
    soup = BeautifulSoup(html, "lxml")

    if rules.list_selector:
        blocks: list[Tag] = soup.select(rules.list_selector)
    else:
        body = soup.body or soup
        blocks = [body] if isinstance(body, Tag) else []

    candidates: list[TenderCandidate] = []
    for block in blocks:
        # Newline separator keeps each element on its own line, so "label: value"
        # captures (authority, deadline) don't bleed into the next field.
        raw_text = block.get_text("\n", strip=True)
        c = TenderCandidate(
            title=_sel_text(block, rules.title_selector),
            reference_number=_sel_text(block, rules.reference_selector),
            contracting_authority=_sel_text(block, rules.authority_selector),
            raw_text=raw_text,
        )

        if rules.regex_fallback_enabled:
            parse_fields(raw_text, language, into=c)

        if not c.title:
            c.title = _fallback_title(block, raw_text)

        # Skip empty blocks (a list_selector that matched layout noise).
        if c.title or c.reference_number:
            candidates.append(c)

    return candidates
