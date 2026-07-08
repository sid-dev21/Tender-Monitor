"""Phase 5 - PDF extractor: text PDFs, real scanned ARCOP detection, no disk writes."""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.models.enums import Language
from app.scrapers.extract.pdf_extractor import extract, looks_like_pdf
from tests.extract.pdf_builder import make_pdf

ARCOP_SCAN = Path(__file__).parent.parent / "fixtures" / "pdfs" / "arcop_31493.pdf"


def test_looks_like_pdf_magic_bytes() -> None:
    assert looks_like_pdf(make_pdf(["hello"])) is True
    assert looks_like_pdf(b"<html>not a pdf</html>") is False


def test_extract_text_pdf_french() -> None:
    pdf = make_pdf(
        [
            "AVIS D'APPEL D'OFFRES N 2025-042",
            "Autorite contractante : Ministere des Infrastructures",
            "Date limite : 15 mars 2026",
            "Montant : 250 000 000 FCFA",
        ]
    )
    c = extract(pdf, Language.FRENCH)

    assert c.is_scanned is False
    assert c.reference_number == "2025-042"
    assert c.deadline == datetime(2026, 3, 15, tzinfo=UTC)
    assert c.estimated_budget == 250_000_000.0


@pytest.mark.skipif(not ARCOP_SCAN.exists(), reason="real ARCOP fixture not present")
def test_real_arcop_scan_is_flagged() -> None:
    """The real ARCOP PDF is a scan - must be detected, not crash, not mis-parse."""
    c = extract(ARCOP_SCAN.read_bytes(), Language.FRENCH)
    assert c.is_scanned is True
    assert c.status().value == "needs_review"


def test_extract_writes_nothing_to_disk(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirect the temp dir to an empty folder and assert extraction creates no files."""
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    before = set(tmp_path.iterdir())

    pdf = make_pdf(["AVIS N 2025-042", "Date limite : 15 mars 2026", "Montant : 250 000 000 FCFA"])
    extract(pdf, Language.FRENCH)

    assert set(tmp_path.iterdir()) == before  # nothing written to disk
