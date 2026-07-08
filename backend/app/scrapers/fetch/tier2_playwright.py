"""Tier 2 fetch: headless Chromium via Playwright.

Used when Tier 1 returns an empty/JS-required page. A real browser runs the page's
JavaScript, so the returned HTML reflects the rendered DOM. Configured with the
target region's locale and timezone for realism.
"""

from __future__ import annotations

from playwright.async_api import async_playwright

from app.core.config import get_settings
from app.core.logging import logger
from app.models.enums import ScrapeTier
from app.scrapers.fetch.result import FetchResult
from app.scrapers.fetch.tier1_httpx import _random_user_agent

VIEWPORT = {"width": 1366, "height": 768}


async def fetch_tier2(
    url: str,
    *,
    locale: str | None = None,
    timezone: str | None = None,
    timeout: float = 30.0,
) -> FetchResult:
    """Fetch a URL with a headless browser. Errors are captured, not raised.

    `locale`/`timezone` set the browser's disguise per-site (e.g. 'de-DE' /
    'Europe/Berlin'); both default to the global settings when not given.
    """
    settings = get_settings()
    locale = locale or settings.scrape_locale
    timezone = timezone or settings.scrape_timezone
    try:
        async with async_playwright() as pw:
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
                    tier_used=ScrapeTier.PLAYWRIGHT,
                    headers=headers,
                )
            finally:
                await browser.close()
    except Exception as exc:  # noqa: BLE001 - browser errors captured as data
        logger.warning("Tier 2 fetch failed for {}: {}", url, exc)
        return FetchResult(
            html="",
            status_code=0,
            final_url=url,
            tier_used=ScrapeTier.PLAYWRIGHT,
            error=str(exc),
        )
