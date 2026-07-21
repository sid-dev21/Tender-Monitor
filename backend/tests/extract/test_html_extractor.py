"""Phase 5 - HTML extractor: config-driven selectors + regex fallback."""

from __future__ import annotations

from datetime import UTC, datetime

from app.models.enums import Language
from app.models.site_config import ExtractionRules
from app.scrapers.extract.html_extractor import extract

PAGE = """
<html><body>
<div class="tenders">
  <article class="tender">
    <h2>Construction d'une ecole a Ouagadougou</h2>
    <p>AVIS D'APPEL D'OFFRES N° 2025-101/MENA</p>
    <p>Autorite contractante : Ministere de l'Education</p>
    <p>Date limite : 20 avril 2026</p>
    <p>Montant : 75 000 000 FCFA</p>
  </article>
  <article class="tender">
    <h2>Rehabilitation de route</h2>
    <p>AVIS D'APPEL D'OFFRES N° 2025-102/MI</p>
    <p>Date limite : 5 mai 2026</p>
    <p>Montant : 500 000 000 FCFA</p>
  </article>
</div>
</body></html>
"""


def test_extract_multiple_tender_blocks() -> None:
    rules = ExtractionRules(list_selector="article.tender", title_selector="h2")
    tenders = extract(PAGE, rules, Language.FRENCH)

    assert len(tenders) == 2

    first = tenders[0]
    assert first.title == "Construction d'une ecole a Ouagadougou"
    assert first.reference_number == "2025-101/MENA"
    assert first.contracting_authority == "Ministere de l'Education"
    assert first.deadline == datetime(2026, 4, 20, tzinfo=UTC)
    assert first.estimated_budget == 75_000_000.0

    assert tenders[1].reference_number == "2025-102/MI"
    assert tenders[1].deadline == datetime(2026, 5, 5, tzinfo=UTC)


def test_no_list_selector_auto_detects_blocks() -> None:
    rules = ExtractionRules()  # no selectors at all
    tenders = extract(PAGE, rules, Language.FRENCH)
    # Auto-detection finds the two <article> tender blocks without any config.
    assert len(tenders) == 2
    assert tenders[0].reference_number == "2025-101/MENA"
    assert tenders[1].reference_number == "2025-102/MI"
