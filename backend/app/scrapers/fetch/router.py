"""TierRouter — the single fetch entry point every engine uses.

Responsibilities:
  1. Start at the tier that last worked for this domain (persisted memory), or
     Tier 1 if unknown.
  2. Run the tier; if the response looks blocked (see signals), escalate 1->2->3.
  3. On success, remember the winning tier for the domain so next time starts there.

Per-domain memory lives in DomainRateLimitState.last_working_tier. Pass a
RateLimitStateRepo to enable persistence; omit it (None) for a stateless fetch.
"""

from __future__ import annotations

from urllib.parse import urlparse

from app.core.logging import logger
from app.models.enums import ScrapeTier
from app.models.site_config import SiteConfig
from app.repositories.rate_limit_repo import RateLimitStateRepo
from app.scrapers.fetch import signals
from app.scrapers.fetch.result import FetchResult
from app.scrapers.fetch.tier1_httpx import fetch_tier1
from app.scrapers.fetch.tier2_playwright import fetch_tier2
from app.scrapers.fetch.tier3_stealth import fetch_tier3

# Escalation order.
_TIER_ORDER: tuple[ScrapeTier, ...] = (
    ScrapeTier.HTTPX,
    ScrapeTier.PLAYWRIGHT,
    ScrapeTier.STEALTH,
)


def domain_of(url: str) -> str:
    """The domain key for a URL (host[:port]), used for per-domain state."""
    return urlparse(url).netloc.lower()


def _tiers_from(start: ScrapeTier) -> tuple[ScrapeTier, ...]:
    """The escalation sequence beginning at `start` (e.g. tier 2 -> (2, 3))."""
    return _TIER_ORDER[_TIER_ORDER.index(start) :]


class TierRouter:
    def __init__(self, rate_limit_repo: RateLimitStateRepo | None = None) -> None:
        self._repo = rate_limit_repo

    async def fetch(self, url: str, *, site: SiteConfig | None = None) -> FetchResult:
        """Fetch `url`, auto-escalating tiers, using the site's locale/timezone if given."""
        locale = site.locale if site else None
        timezone = site.timezone if site else None
        domain = domain_of(url)

        start = await self._starting_tier(domain)
        result: FetchResult | None = None
        for tier in _tiers_from(start):
            result = await self._run_tier(tier, url, locale, timezone)
            escalate, reason = signals.should_escalate(
                result.status_code, result.headers, result.html
            )
            if not escalate:
                await self._remember(domain, tier)
                return result
            logger.info(
                "Escalating past tier {} for {} ({})", int(tier), domain, reason
            )

        # All tiers exhausted; return the last (blocked/failed) result.
        logger.warning("All tiers exhausted for {}", domain)
        return result  # type: ignore[return-value]  # loop always runs at least once

    async def _starting_tier(self, domain: str) -> ScrapeTier:
        if self._repo is not None:
            state = await self._repo.find_by_domain(domain)
            if state is not None and state.last_working_tier is not None:
                return state.last_working_tier
        return ScrapeTier.HTTPX

    async def _run_tier(
        self, tier: ScrapeTier, url: str, locale: str | None, timezone: str | None
    ) -> FetchResult:
        if tier == ScrapeTier.HTTPX:
            return await fetch_tier1(url, locale=locale)
        if tier == ScrapeTier.PLAYWRIGHT:
            return await fetch_tier2(url, locale=locale, timezone=timezone)
        return await fetch_tier3(url, locale=locale, timezone=timezone)

    async def _remember(self, domain: str, tier: ScrapeTier) -> None:
        if self._repo is not None:
            await self._repo.apply(domain, {"$set": {"last_working_tier": int(tier)}})
