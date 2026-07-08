"""Phase 5 - multi-language field parser (French / German / English)."""

from __future__ import annotations

from datetime import UTC, datetime

from app.models.enums import Language, TenderStatus
from app.scrapers.extract.field_parser import _parse_amount, parse_fields

FRENCH_TEXT = """AVIS D'APPEL D'OFFRES N° 2025-042/MEBF
Autorité contractante : Ministère des Infrastructures
Date limite de dépôt des offres : 15 mars 2026
Montant estimé : 250 000 000 FCFA
"""

GERMAN_TEXT = """Ausschreibung Nr. DE-2026-0123
Vergabestelle: Bundesamt für Bauwesen
Angebotsfrist: 12.03.2026
Geschätzter Wert: 1.250.000,00 EUR
"""

ENGLISH_TEXT = """Invitation to Tender No. UK-2026-77
Contracting Authority: City of London Council
Closing Date: 12 March 2026
Estimated Value: GBP 2,500,000.00
"""


def test_parse_french() -> None:
    c = parse_fields(FRENCH_TEXT, Language.FRENCH)
    assert c.reference_number == "2025-042/MEBF"
    assert c.contracting_authority == "Ministère des Infrastructures"
    assert c.deadline == datetime(2026, 3, 15, tzinfo=UTC)
    assert c.estimated_budget == 250_000_000.0
    assert c.currency == "XOF"
    assert c.status() == TenderStatus.PARSED  # 4 core fields


def test_parse_german() -> None:
    c = parse_fields(GERMAN_TEXT, Language.GERMAN)
    assert c.reference_number == "DE-2026-0123"
    assert c.contracting_authority == "Bundesamt für Bauwesen"
    assert c.deadline == datetime(2026, 3, 12, tzinfo=UTC)
    assert c.estimated_budget == 1_250_000.00
    assert c.currency == "EUR"


def test_parse_english() -> None:
    c = parse_fields(ENGLISH_TEXT, Language.ENGLISH)
    assert c.reference_number == "UK-2026-77"
    assert c.contracting_authority == "City of London Council"
    assert c.deadline == datetime(2026, 3, 12, tzinfo=UTC)
    assert c.estimated_budget == 2_500_000.00
    assert c.currency == "GBP"


def test_language_from_locale() -> None:
    assert Language.from_locale("de-DE") == Language.GERMAN
    assert Language.from_locale("fr-FR") == Language.FRENCH
    assert Language.from_locale("en-GB") == Language.ENGLISH
    assert Language.from_locale(None) == Language.FRENCH  # default


def test_parse_amount_variants() -> None:
    assert _parse_amount("250 000 000") == 250_000_000.0
    assert _parse_amount("1.250.000,00") == 1_250_000.00   # european
    assert _parse_amount("2,500,000.00") == 2_500_000.00   # anglo
    assert _parse_amount("42") == 42.0


def test_low_confidence_is_needs_review() -> None:
    c = parse_fields("Some unrelated text with no tender fields at all.", Language.ENGLISH)
    assert c.status() == TenderStatus.NEEDS_REVIEW
