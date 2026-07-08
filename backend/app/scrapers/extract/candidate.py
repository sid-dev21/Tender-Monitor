"""TenderCandidate — extracted fields before they become a persisted Tender.

Confidence rule: a tender needs >= 4 of the core fields to be considered "parsed";
fewer means "needs_review" (a human, or later the AI extractor, should look).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.models.enums import TenderStatus

# Core fields that count toward the confidence score.
_CORE_FIELDS = (
    "title",
    "reference_number",
    "publication_date",
    "deadline",
    "contracting_authority",
    "estimated_budget",
)
MIN_FIELDS_FOR_PARSED = 4


@dataclass
class TenderCandidate:
    title: str | None = None
    reference_number: str | None = None
    publication_date: datetime | None = None
    deadline: datetime | None = None
    contracting_authority: str | None = None
    sector: str | None = None
    estimated_budget: float | None = None
    currency: str = "XOF"
    document_url: str | None = None
    raw_text: str | None = None
    is_scanned: bool = False  # set when a PDF is an image scan (no extractable text)
    extra: dict[str, str] = field(default_factory=dict)

    def field_count(self) -> int:
        """How many core fields were successfully extracted."""
        return sum(getattr(self, name) is not None for name in _CORE_FIELDS)

    def status(self) -> TenderStatus:
        return (
            TenderStatus.PARSED
            if self.field_count() >= MIN_FIELDS_FOR_PARSED
            else TenderStatus.NEEDS_REVIEW
        )
