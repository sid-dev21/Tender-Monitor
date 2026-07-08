"""Phase 2 — Tier 1 httpx fetch against a real local HTTP server (no mocks)."""

from __future__ import annotations

from app.models.enums import ScrapeTier
from app.scrapers.fetch.tier1_httpx import fetch_tier1
from tests.scrapers.conftest import LocalServer


async def test_tier1_fetches_ok(http_server: LocalServer) -> None:
    url = http_server.add(
        "/avis", "<html><body><h1>Appels d'offres BTP</h1></body></html>"
    )
    result = await fetch_tier1(url)

    assert result.ok
    assert result.status_code == 200
    assert result.tier_used == ScrapeTier.HTTPX
    assert "appels d'offres" in result.html.lower()
    assert result.error is None


async def test_tier1_reports_block_status(http_server: LocalServer) -> None:
    """A 403 comes back as a non-ok result the router can escalate on."""
    url = http_server.add("/blocked", "Forbidden", status=403)
    result = await fetch_tier1(url)

    assert result.ok is False
    assert result.status_code == 403


async def test_tier1_captures_connection_error() -> None:
    """An unreachable host is captured into result.error, not raised."""
    # Port 1 on localhost: nothing listens there -> connection refused.
    result = await fetch_tier1("http://127.0.0.1:1/", timeout=2.0)

    assert result.ok is False
    assert result.status_code == 0
    assert result.error is not None
