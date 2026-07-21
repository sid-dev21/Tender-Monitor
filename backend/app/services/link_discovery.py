"""Discover likely tender-listing sub-pages from a page's links.

When a user points a source at a site's homepage, the tenders are usually on a
sub-page (/appels-offres, /marches-publics, ...). This scans anchors for
procurement keywords (FR/DE/EN) and suggests same-site links to re-test.
"""

from __future__ import annotations

import unicodedata
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

# Keywords (accent-free, lowercase) that suggest a tenders section.
_KEYWORDS = (
    "appel",
    "offre",
    "marche",
    "avis",
    "soumission",
    "consultation",
    "tender",
    "procurement",
    "ausschreibung",
    "vergabe",
    "telechargement",
)


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.lower()


def discover_tender_links(
    html: str, base_url: str, *, limit: int = 8
) -> list[dict[str, str]]:
    """Return up to `limit` same-site links whose text/href suggests tenders."""
    soup = BeautifulSoup(html, "lxml")
    base_host = urlparse(base_url).netloc.lower()
    seen: set[str] = set()
    out: list[dict[str, str]] = []

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        text = anchor.get_text(" ", strip=True)
        haystack = _norm(f"{text} {href}")
        if not any(kw in haystack for kw in _KEYWORDS):
            continue

        full = urljoin(base_url, href)
        parsed = urlparse(full)
        if parsed.scheme not in ("http", "https") or parsed.netloc.lower() != base_host:
            continue
        if full == base_url.rstrip("/") or full in seen:
            continue

        seen.add(full)
        out.append({"url": full, "label": (text[:70] or full)})
        if len(out) >= limit:
            break

    return out
