"""Phase 2 - Tier 2 Playwright renders JS-injected content (real browser, no mocks).

Proves the browser tier sees content that only exists after JavaScript runs -
exactly the case where Tier 1 (raw HTTP) falls short.
"""

from __future__ import annotations

from app.models.enums import ScrapeTier
from app.scrapers.fetch.tier1_httpx import fetch_tier1
from app.scrapers.fetch.tier2_playwright import fetch_tier2
from tests.scrapers.conftest import LocalServer

# The reference is ASSEMBLED at runtime, so the literal "AON-2025-777" exists only
# in the rendered DOM - never in the page source. That makes the Tier 1 vs Tier 2
# contrast real: raw HTTP can't produce a string the source never contained.
JS_PAGE = """
<html><body>
  <div id="app">loading</div>
  <script>
    setTimeout(function () {
      var ref = 'AON-' + '2025-' + '777';
      document.getElementById('app').textContent = 'Avis ' + ref;
    }, 100);
  </script>
</body></html>
"""


async def test_tier2_renders_javascript(http_server: LocalServer) -> None:
    url = http_server.add("/spa", JS_PAGE)

    result = await fetch_tier2(url)

    assert result.ok
    assert result.tier_used == ScrapeTier.PLAYWRIGHT
    assert "AON-2025-777" in result.html  # assembled by JS, so only a browser sees it


async def test_tier1_cannot_see_js_content(http_server: LocalServer) -> None:
    """Contrast: raw HTTP gets the pre-JS markup only - the motivation for Tier 2."""
    url = http_server.add("/spa", JS_PAGE)

    result = await fetch_tier1(url)

    assert result.ok
    assert "AON-2025-777" not in result.html  # never in source; only assembled at runtime
    assert "loading" in result.html.lower()
