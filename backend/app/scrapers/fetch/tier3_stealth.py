"""Tier 3 fetch: Playwright with playwright-stealth fingerprint hardening.

Same as Tier 2, but every page is patched to hide automation tells (navigator.
webdriver, headless markers, WebGL vendor, etc.). Used when Tier 2 still gets
blocked (Cloudflare, 403/429). Heaviest and slowest tier; last resort.
"""

from __future__ import annotations

from playwright.async_api import async_playwright
from playwright_stealth import Stealth

from app.core.config import get_settings
from app.core.logging import logger
from app.models.enums import ScrapeTier
from app.scrapers.fetch.result import FetchResult
from app.scrapers.fetch.tier1_httpx import _random_user_agent
from app.scrapers.fetch.tier2_playwright import VIEWPORT


async def fetch_tier3(
    url: str,
    *,
    locale: str | None = None,
    timezone: str | None = None,
    timeout: float = 40.0,
) -> FetchResult:
    """Fetch a URL with a stealth-hardened headless browser. Errors captured, not raised."""
    settings = get_settings()
    locale = locale or settings.scrape_locale
    timezone = timezone or settings.scrape_timezone
    try:
        # Stealth.use_async wraps async_playwright and auto-applies evasions to
        # every context/page created within the block.
        async with Stealth().use_async(async_playwright()) as pw:
            browser = await pw.chromium.launch(headless=settings.playwright_headless)
            try:
                context = await browser.new_context(
                    locale=locale,
                    timezone_id=timezone,
                    user_agent=_random_user_agent(),
                    viewport=VIEWPORT,
                )
                page = await context.new_page()
                response = await page.goto(
                    url, wait_until="networkidle", timeout=timeout * 1000
                )
                html = await page.content()
                status = response.status if response is not None else 0
                headers = (
                    {k.lower(): v for k, v in response.headers.items()}
                    if response is not None
                    else {}
                )
                return FetchResult(
                    html=html,
                    status_code=status,
                    final_url=page.url,
                    tier_used=ScrapeTier.STEALTH,
                    headers=headers,
                )
            finally:
                await browser.close()
    except Exception as exc:  # noqa: BLE001 - browser errors captured as data
        logger.warning("Tier 3 fetch failed for {}: {}", url, exc)
        return FetchResult(
            html="",
            status_code=0,
            final_url=url,
            tier_used=ScrapeTier.STEALTH,
            error=str(exc),
        )
