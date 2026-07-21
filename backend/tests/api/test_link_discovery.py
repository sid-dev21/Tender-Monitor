"""Phase 7+ - tender sub-page link discovery (pure, offline)."""

from __future__ import annotations

from app.services.link_discovery import discover_tender_links

HOMEPAGE = """
<html><body>
  <nav>
    <a href="/accueil">Accueil</a>
    <a href="/appels-offres">Appels d'offres en cours</a>
    <a href="/marches-publics/avis">Avis de marchés</a>
    <a href="https://other-site.bf/tenders">External tenders</a>
    <a href="/contact">Contact</a>
    <a href="/telechargement/123">Télécharger l'avis</a>
  </nav>
</body></html>
"""


def test_discovers_same_site_tender_links() -> None:
    links = discover_tender_links(HOMEPAGE, "https://exemple.bf")
    urls = [link["url"] for link in links]

    assert "https://exemple.bf/appels-offres" in urls
    assert "https://exemple.bf/marches-publics/avis" in urls
    assert "https://exemple.bf/telechargement/123" in urls
    # External and irrelevant links are excluded.
    assert "https://other-site.bf/tenders" not in urls
    assert all("contact" not in u and "accueil" not in u for u in urls)


def test_no_matches_returns_empty() -> None:
    html = "<html><body><a href='/about'>About</a><a href='/home'>Home</a></body></html>"
    assert discover_tender_links(html, "https://exemple.bf") == []
