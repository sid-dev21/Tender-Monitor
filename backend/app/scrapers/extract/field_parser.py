"""Multi-language field parser (French / German / English).

Extracts procurement fields from free text using per-language patterns. Used by
both extractors: HTML selectors fill what they can, then this fills the gaps; for
text PDFs it does the whole job. Scanned PDFs bypass this entirely (see roadmap).
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

from app.models.enums import Language
from app.scrapers.extract.candidate import TenderCandidate

# --------------------------------------------------------------------------- #
# Month name -> number, per language
# --------------------------------------------------------------------------- #
_FR_MONTHS = {
    "janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5,
    "juin": 6, "juillet": 7, "août": 8, "aout": 8, "septembre": 9,
    "octobre": 10, "novembre": 11, "décembre": 12, "decembre": 12,
}
_DE_MONTHS = {
    "januar": 1, "februar": 2, "märz": 3, "maerz": 3, "april": 4, "mai": 5,
    "juni": 6, "juli": 7, "august": 8, "september": 9, "oktober": 10,
    "november": 11, "dezember": 12,
}
_EN_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12, "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7,
    "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}
_MONTHS = {Language.FRENCH: _FR_MONTHS, Language.GERMAN: _DE_MONTHS, Language.ENGLISH: _EN_MONTHS}

# Keywords that introduce the SUBMISSION DEADLINE, per language.
_DEADLINE_KEYWORDS = {
    Language.FRENCH: [
        "date limite", "au plus tard", "avant le", "date de dépôt", "date de depot",
        "clôture", "cloture", "délai de soumission", "delai de soumission",
    ],
    Language.GERMAN: [
        "angebotsfrist", "einreichungsfrist", "abgabefrist", "schlusstermin",
        "frist", "spätestens", "spaetestens",
    ],
    Language.ENGLISH: [
        "closing date", "submission deadline", "deadline", "no later than",
        "due date", "closing time",
    ],
}

# Keywords that introduce the PUBLICATION date.
_PUBLICATION_KEYWORDS = {
    Language.FRENCH: ["publié le", "publie le", "date de publication", "le"],
    Language.GERMAN: ["veröffentlicht am", "veroeffentlicht am", "bekanntmachung vom"],
    Language.ENGLISH: ["published on", "publication date", "date of publication"],
}

# Labels that introduce the CONTRACTING AUTHORITY.
_AUTHORITY_LABELS = {
    Language.FRENCH: ["autorité contractante", "autorite contractante", "maître d'ouvrage",
                      "maitre d'ouvrage", "maître d’ouvrage"],
    Language.GERMAN: ["vergabestelle", "auftraggeber", "auftraggeberin"],
    Language.ENGLISH: ["contracting authority", "procuring entity", "contracting entity"],
}

# Reference-number patterns (tried in order); generic fallback last.
_REFERENCE_PATTERNS = {
    Language.FRENCH: [
        r"(?:avis\s+d['’]appel\s+d['’]offres?|a\.?a\.?o\.?|a\.?o\.?n\.?|appel\s+d['’]offres?)"
        r"\s*n[°ºo]?\s*[:\-]?\s*([A-Za-z0-9][\w\-/\.]{2,})",
    ],
    Language.GERMAN: [
        r"(?:ausschreibung|vergabe(?:nummer)?|bekanntmachungsnummer|referenz)"
        r"\s*(?:nr\.?|nummer)?\s*[:\-]?\s*([A-Za-z0-9][\w\-/\.]{2,})",
    ],
    Language.ENGLISH: [
        r"(?:invitation\s+to\s+tender|tender|reference|rfp|rfq)"
        r"\s*(?:no\.?|number|ref\.?)?\s*[:\-]?\s*([A-Za-z0-9][\w\-/\.]{2,})",
    ],
}
# Require a real reference marker: "N°", "No.", "Nr." — NOT a bare "no", which
# matches inside ordinary words ("dénonciations", "notification").
_GENERIC_REFERENCE = r"\bn(?:[°º]|o\.|r\.)\s*[:\-]?\s*([A-Za-z0-9][\w\-/\.]{2,})"

# Amounts below this are noise (page numbers, counts), never a tender budget.
_MIN_PLAUSIBLE_BUDGET = 1000.0

# Currency token -> ISO code.
_CURRENCY_PATTERNS: list[tuple[str, str]] = [
    (r"f\s?cfa|fcfa|xof", "XOF"),
    (r"€|eur\b|euros?", "EUR"),
    (r"£|gbp\b", "GBP"),
    (r"us\$|\$|usd\b", "USD"),
]

_NUMERIC_DATE = re.compile(r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b")
_ISO_DATE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")


def _text_month_date(segment: str, language: Language) -> datetime | None:
    """Parse a 'DD Month YYYY' / 'Month DD, YYYY' date using language month names."""
    months = _MONTHS[language]
    names = "|".join(sorted(months, key=len, reverse=True))
    # DD Month YYYY (fr/de and en "12 March 2026")
    m = re.search(rf"\b(\d{{1,2}})\.?\s+({names})\.?\s+(\d{{4}})\b", segment, re.IGNORECASE)
    if m:
        return datetime(int(m.group(3)), months[m.group(2).lower()], int(m.group(1)), tzinfo=UTC)
    # Month DD, YYYY (english)
    m = re.search(rf"\b({names})\s+(\d{{1,2}}),?\s+(\d{{4}})\b", segment, re.IGNORECASE)
    if m:
        return datetime(int(m.group(3)), months[m.group(1).lower()], int(m.group(2)), tzinfo=UTC)
    return None


def _find_date(segment: str, language: Language) -> datetime | None:
    """Find the first date in a text segment (text-month, then dd/mm/yyyy, then ISO)."""
    dt = _text_month_date(segment, language)
    if dt:
        return dt
    m = _NUMERIC_DATE.search(segment)
    if m:
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= month <= 12 and 1 <= day <= 31:
            return datetime(year, month, day, tzinfo=UTC)
    m = _ISO_DATE.search(segment)
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=UTC)
    return None


def _parse_amount(raw: str) -> float | None:
    """Turn '250 000 000' / '1.234.567,89' / '1,234,567.89' into a float."""
    raw = raw.replace(" ", " ").strip()
    dec = re.search(r"[.,](\d{1,2})$", raw)
    if dec:
        int_part = re.sub(r"\D", "", raw[: dec.start()])
        return float(f"{int_part}.{dec.group(1)}") if int_part else None
    digits = re.sub(r"\D", "", raw)
    return float(digits) if digits else None


def _find_budget(text: str) -> tuple[float | None, str | None]:
    """Find an amount adjacent to a currency token; return (amount, iso_currency)."""
    lower = text.lower()
    for pattern, iso in _CURRENCY_PATTERNS:
        # amount BEFORE currency:  250 000 000 FCFA
        m = re.search(rf"([\d][\d ., ]*\d)\s*(?:{pattern})", lower)
        if not m:
            # amount AFTER currency:  EUR 1.234.567,89
            m = re.search(rf"(?:{pattern})\s*([\d][\d ., ]*\d)", lower)
        if m:
            amount = _parse_amount(m.group(1))
            if amount is not None and amount >= _MIN_PLAUSIBLE_BUDGET:
                return amount, iso
    return None, None


def _is_date_like(token: str) -> bool:
    """A reference must not actually be a date (e.g. '14/05/2026')."""
    return bool(_NUMERIC_DATE.fullmatch(token) or _ISO_DATE.fullmatch(token))


def _find_reference(text: str, language: Language) -> str | None:
    for pattern in _REFERENCE_PATTERNS[language]:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            token = m.group(1).rstrip(".")
            if not _is_date_like(token):
                return token
    m = re.search(_GENERIC_REFERENCE, text, re.IGNORECASE)
    if m:
        token = m.group(1).rstrip(".")
        if not _is_date_like(token):
            return token
    return None


def _find_labeled(text: str, labels: list[str]) -> str | None:
    """Return the text after 'label :' on the same line, for the first matching label."""
    for label in labels:
        m = re.search(rf"{re.escape(label)}\s*[:\-]\s*(.+)", text, re.IGNORECASE)
        if m:
            return m.group(1).splitlines()[0].strip() or None
    return None


def _find_deadline(text: str, language: Language) -> datetime | None:
    """Find a date near a deadline keyword."""
    lower = text.lower()
    for kw in _DEADLINE_KEYWORDS[language]:
        idx = lower.find(kw)
        if idx != -1:
            segment = text[idx : idx + 80]
            dt = _find_date(segment, language)
            if dt:
                return dt
    return None


def parse_fields(
    text: str, language: Language = Language.FRENCH, into: TenderCandidate | None = None
) -> TenderCandidate:
    """Fill a TenderCandidate from `text`. Only fills fields that are still None."""
    c = into or TenderCandidate()
    c.raw_text = c.raw_text or text

    if c.reference_number is None:
        c.reference_number = _find_reference(text, language)
    if c.contracting_authority is None:
        c.contracting_authority = _find_labeled(text, _AUTHORITY_LABELS[language])
    if c.deadline is None:
        c.deadline = _find_deadline(text, language)
    if c.estimated_budget is None:
        amount, currency = _find_budget(text)
        if amount is not None:
            c.estimated_budget = amount
            c.currency = currency or c.currency
    if c.publication_date is None:
        pub_label = _find_labeled(text, _PUBLICATION_KEYWORDS[language])
        c.publication_date = _find_date(pub_label, language) if pub_label else None

    return c
