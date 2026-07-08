"""Phase 2 - TierRouter escalation + per-domain tier memory (real browser + Mongo)."""

from __future__ import annotations

from app.models.enums import ScrapeTier
from app.repositories.rate_limit_repo import RateLimitStateRepo
from app.scrapers.fetch.router import TierRouter, domain_of
from tests.scrapers.conftest import LocalServer

PADDED_PAGE = "<html><body>" + "<p>Appel d'offres BTP</p>" * 40 + "</body></html>"


async def test_router_stays_on_tier1_for_static(http_server: LocalServer, db) -> None:  # noqa: ANN001
    """A healthy static page succeeds on Tier 1 - no escalation."""
    url = http_server.add("/static", PADDED_PAGE)
    router = TierRouter(RateLimitStateRepo(db))

    result = await router.fetch(url)

    assert result.ok
    assert result.tier_used == ScrapeTier.HTTPX
    # Winning tier remembered for the domain.
    state = await RateLimitStateRepo(db).find_by_domain(domain_of(url))
    assert state is not None
    assert state.last_working_tier == ScrapeTier.HTTPX


async def test_router_escalates_httpx_to_browser(http_server: LocalServer, db) -> None:  # noqa: ANN001
    """A page that 403s raw HTTP but serves to a browser forces Tier 1 -> Tier 2."""
    url = http_server.add_browser_gated("/protected", PADDED_PAGE)
    repo = RateLimitStateRepo(db)
    router = TierRouter(repo)

    result = await router.fetch(url)

    assert result.ok
    assert result.tier_used == ScrapeTier.PLAYWRIGHT  # escalated from httpx
    state = await repo.find_by_domain(domain_of(url))
    assert state is not None
    assert state.last_working_tier == ScrapeTier.PLAYWRIGHT


async def test_router_starts_at_remembered_tier(http_server: LocalServer, db) -> None:  # noqa: ANN001
    """If the domain last worked on Tier 2, the router starts there (skips Tier 1)."""
    url = http_server.add("/x", PADDED_PAGE)
    repo = RateLimitStateRepo(db)
    domain = domain_of(url)
    # Seed memory: this domain last worked on the browser tier.
    await repo.apply(domain, {"$set": {"last_working_tier": int(ScrapeTier.PLAYWRIGHT)}})

    result = await TierRouter(repo).fetch(url)

    # Even though /x would work on Tier 1, memory made it start on Tier 2.
    assert result.tier_used == ScrapeTier.PLAYWRIGHT
