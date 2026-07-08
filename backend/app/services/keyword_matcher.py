"""Keyword matching: which of a user's keywords appear in a tender's text.

Matching is accent- and case-insensitive substring on the tender's title + raw
text (both normalized). Used at query time (tenders list) and at notification time
(which tenders match a user since last_sent_at).
"""

from __future__ import annotations

from app.models.tender import Tender
from app.services.keyword_normalizer import normalize


def _blob(tender: Tender) -> str:
    return normalize(f"{tender.title or ''} {tender.raw_text or ''}")


def matched_keywords(tender: Tender, keywords: list[str]) -> list[str]:
    """Return the subset of `keywords` (already-normalized) found in the tender."""
    blob = _blob(tender)
    return [kw for kw in keywords if kw and kw in blob]


def filter_tenders(tenders: list[Tender], keywords: list[str]) -> list[Tender]:
    """Keep tenders that match at least one keyword. Empty keywords => keep all."""
    if not keywords:
        return tenders
    return [t for t in tenders if matched_keywords(t, keywords)]
