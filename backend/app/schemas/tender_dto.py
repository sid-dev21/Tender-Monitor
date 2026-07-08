"""Request/response schemas for tenders and keyword management."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.tender import Tender


class KeywordsUpdateRequest(BaseModel):
    keywords: list[str] = Field(default_factory=list)


class TenderResponse(BaseModel):
    id: str
    title: str
    reference_number: str
    publication_date: datetime | None
    deadline: datetime | None
    contracting_authority: str | None
    estimated_budget: float | None
    currency: str
    status: str
    document_url: str | None
    source_site_id: str
    matched_keywords: list[str]
    created_at: datetime

    @classmethod
    def from_tender(cls, t: Tender, matched: list[str] | None = None) -> "TenderResponse":
        return cls(
            id=str(t.id),
            title=t.title,
            reference_number=t.reference_number,
            publication_date=t.publication_date,
            deadline=t.deadline,
            contracting_authority=t.contracting_authority,
            estimated_budget=t.estimated_budget,
            currency=t.currency,
            status=t.status.value,
            document_url=t.document_url,
            source_site_id=str(t.source_site_id),
            matched_keywords=matched or [],
            created_at=t.created_at,
        )
