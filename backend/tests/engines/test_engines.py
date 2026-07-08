"""Phase 6 - generic engines end to end (real HTTP server + real Mongo, no mocks)."""

from __future__ import annotations

from bson import ObjectId

from app.models.enums import ContentType
from app.models.site_config import ExtractionRules, SiteConfig
from app.repositories.site_config_repo import SiteConfigRepo
from app.repositories.tender_repo import TenderRepo
from app.scrapers.orchestrator import run_scrape
from tests.conftest import LocalServer
from tests.extract.pdf_builder import make_pdf

HTML_PAGE = """
<html><body>
<div class="tenders">
  <article class="tender">
    <h2>Construction d'une ecole a Ouagadougou</h2>
    <p>AVIS D'APPEL D'OFFRES N 2025-101/MENA</p>
    <p>Autorite contractante : Ministere de l'Education</p>
    <p>Date limite : 20 avril 2026</p>
    <p>Montant : 75 000 000 FCFA</p>
  </article>
  <article class="tender">
    <h2>Rehabilitation de route nationale</h2>
    <p>AVIS D'APPEL D'OFFRES N 2025-102/MI</p>
    <p>Date limite : 5 mai 2026</p>
    <p>Montant : 500 000 000 FCFA</p>
  </article>
</div>
</body></html>
"""

PDF1 = make_pdf(
    ["AVIS D'APPEL D'OFFRES N 2025-201", "Date limite : 10 juin 2026", "Montant : 100 000 000 FCFA"]
)
PDF2 = make_pdf(
    ["AVIS D'APPEL D'OFFRES N 2025-202", "Date limite : 20 juin 2026", "Montant : 200 000 000 FCFA"]
)
LANDING = (
    "<html><body>"
    + "<p>Portail des appels d'offres publics BTP du Burkina Faso.</p>" * 20
    + '<a href="/doc1">Avis 1</a><a href="/doc2">Avis 2</a>'
    + "</body></html>"
)


def _html_site(url: str) -> SiteConfig:
    return SiteConfig(
        name="Test HTML source",
        base_url=url,
        content_type=ContentType.HTML,
        extraction_rules=ExtractionRules(list_selector="article.tender", title_selector="h2"),
        created_by_user_id=ObjectId(),
    )


async def test_html_engine_scrapes_and_saves(http_server: LocalServer, db) -> None:  # noqa: ANN001
    url = http_server.add("/tenders", HTML_PAGE)
    site = await SiteConfigRepo(db).insert(_html_site(url))

    result = await run_scrape(site.id, db)

    assert result.new_count == 2
    assert await TenderRepo(db).count() == 2
    assert result.run is not None and result.run.tenders_found == 2
    assert all(t.extraction_type == ContentType.HTML for t in result.tenders)
    refs = {t.reference_number for t in result.tenders}
    assert refs == {"2025-101/MENA", "2025-102/MI"}


async def test_pdf_engine_streams_and_saves(http_server: LocalServer, db) -> None:  # noqa: ANN001
    http_server.add_bytes("/doc1", PDF1)
    http_server.add_bytes("/doc2", PDF2)
    landing = http_server.add("/avis", LANDING)
    site = await SiteConfigRepo(db).insert(
        SiteConfig(
            name="Test PDF source",
            base_url=landing,
            content_type=ContentType.PDF,
            extraction_rules=ExtractionRules(pdf_link_selector="a"),
            created_by_user_id=ObjectId(),
        )
    )

    result = await run_scrape(site.id, db)

    assert result.new_count == 2
    refs = {t.reference_number for t in result.tenders}
    assert refs == {"2025-201", "2025-202"}
    assert all(t.extraction_type == ContentType.PDF for t in result.tenders)


async def test_dedup_on_second_run(http_server: LocalServer, db) -> None:  # noqa: ANN001
    url = http_server.add("/tenders", HTML_PAGE)
    site = await SiteConfigRepo(db).insert(_html_site(url))

    first = await run_scrape(site.id, db)
    second = await run_scrape(site.id, db)

    assert first.new_count == 2
    assert second.new_count == 0                 # nothing new on the second run
    assert await TenderRepo(db).count() == 2      # no duplicates
    tender = (await TenderRepo(db).find({}))[0]
    assert tender.times_seen == 2                  # re-seen, not re-created


async def test_add_new_site_requires_no_python_code(http_server: LocalServer, db) -> None:  # noqa: ANN001
    """The architecture's core promise: a brand-new site is just a Mongo document.

    Nothing about this URL is referenced anywhere in engine code. Inserting a
    SiteConfig and calling run_scrape yields tenders - zero new Python written.
    """
    url = http_server.add("/a-source-never-seen-in-code", HTML_PAGE)
    site = await SiteConfigRepo(db).insert(
        SiteConfig(
            name="Brand New Source Added As Data",
            base_url=url,
            content_type=ContentType.HTML,
            extraction_rules=ExtractionRules(list_selector="article.tender", title_selector="h2"),
            created_by_user_id=ObjectId(),
        )
    )

    result = await run_scrape(site.id, db)

    assert result.new_count == 2
