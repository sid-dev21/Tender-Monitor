"""Tier 1 fetch: plain httpx with a rotating User-Agent and realistic headers.

Fast and lightweight — the default for static sites. Returns a FetchResult; never
raises on network errors (they are captured into result.error so the router can
decide to escalate or record the failure).
"""

from __future__ import annotations

import httpx

from app.core.config import get_settings
from app.core.logging import logger
from app.models.enums import ScrapeTier
from app.scrapers.fetch.result import FetchResult

# Fallback UA if fake-useragent is unavailable for any reason.
_FALLBACK_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def _random_user_agent() -> str:
    try:
        from fake_useragent import UserAgent

        return UserAgent().random
    except Exception:  # noqa: BLE001 - never let UA sourcing break a fetch
        return _FALLBACK_UA


def _accept_language(locale: str) -> str:
    """Build an Accept-Language header from a locale like 'fr-FR' or 'de-DE'."""
    lang = locale.split("-")[0]
    return f"{locale},{lang};q=0.9,en;q=0.8"


def _browser_headers(locale: str) -> dict[str, str]:
    """Headers that make an httpx request look like a real browser in `locale`."""
    return {
        "User-Agent": _random_user_agent(),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": _accept_language(locale),
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }


async def fetch_tier1(
    url: str, *, locale: str | None = None, timeout: float = 20.0
) -> FetchResult:
    """Fetch a URL with httpx. Returns a FetchResult (errors captured, not raised).

    `locale` (e.g. 'de-DE') sets Accept-Language; defaults to settings.scrape_locale.
    """
    locale = locale or get_settings().scrape_locale
    try:
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=timeout, headers=_browser_headers(locale)
        ) as client:
            resp = await client.get(url)
            return FetchResult(
                html=resp.text,
                status_code=resp.status_code,
                final_url=str(resp.url),
                tier_used=ScrapeTier.HTTPX,
                headers={k.lower(): v for k, v in resp.headers.items()},
            )
    except httpx.HTTPError as exc:
        logger.warning("Tier 1 fetch failed for {}: {}", url, exc)
        return FetchResult(
            html="",
            status_code=0,
            final_url=url,
            tier_used=ScrapeTier.HTTPX,
            error=str(exc),
        )
