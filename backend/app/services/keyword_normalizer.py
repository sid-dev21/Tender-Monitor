"""Keyword normalization: lowercase, strip accents, collapse whitespace, dedupe.

Accent-stripping matters for French: a user typing "ecole" should match "école".
"""

from __future__ import annotations

import re
import unicodedata


def normalize(keyword: str) -> str:
    """Lowercase, remove accents/diacritics, and collapse whitespace."""
    decomposed = unicodedata.normalize("NFKD", keyword)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", without_accents).strip().lower()


def normalize_list(keywords: list[str], *, max_items: int = 50) -> list[str]:
    """Normalize, drop empties, dedupe (order-preserving), and cap the count."""
    seen: list[str] = []
    for kw in keywords:
        n = normalize(kw)
        if n and n not in seen:
            seen.append(n)
    return seen[:max_items]
