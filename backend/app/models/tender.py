"""Tender — a single public-procurement notice extracted from a source site."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.base import MongoModel
from app.models.enums import ContentType, ScrapeTier, TenderStatus
from app.models.objectid import PyObjectId


class MatchedUser(BaseModel):
    """Which keywords of a given user this tender matched (filled in Phase 8)."""

    user_id: PyObjectId
    keywords: list[str] = Field(default_factory=list)


class Tender(MongoModel):
    """A tender notice, stored in the `tenders` collection.

    Deduplication identity is the pair (reference_number, source_site_id): the same
    reference from the same site is the SAME tender, even across many scrape runs. A
    unique index on that pair (init_indexes.py) enforces this at the database level,
    and the repository upserts on it, bumping `times_seen` instead of duplicating.
    """

    # --- Core procurement fields ---
    title: str
    reference_number: str                     # part of the dedup key
    publication_date: datetime | None = None
    deadline: datetime | None = None
    contracting_authority: str | None = None
    sector: str | None = None
    estimated_budget: float | None = None
    currency: str = "XOF"                     # West African CFA franc (FCFA)
    document_url: str | None = None           # link to the source PDF/page

    # --- Provenance / dedup ---
    source_site_id: PyObjectId                # part of the dedup key
    extraction_type: ContentType              # which engine produced it
    scrape_tier_used: ScrapeTier | None = None
    raw_text: str | None = None               # full extracted text (for keyword search)

    # --- Quality & lifecycle ---
    status: TenderStatus = TenderStatus.NEEDS_REVIEW
    times_seen: int = 1                        # incremented on each re-scrape

    # --- Keyword matching (populated by the matcher in Phase 8) ---
    keywords_matched: list[str] = Field(default_factory=list)   # union across all users
    matched_users: list[MatchedUser] = Field(default_factory=list)  # per-user breakdown
