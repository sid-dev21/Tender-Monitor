"""ScraperRun — an audit record of a single scrape execution."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.models.base import MongoModel, utcnow
from app.models.enums import ScrapeTier
from app.models.objectid import PyObjectId


class ScraperRun(MongoModel):
    """One execution of an engine against one site, stored in `scraper_runs`.

    Written whether the run succeeds or fails. A non-empty `errors` list means the
    run hit problems (per-block failures, timeouts, blocked PDFs) but the engine
    keeps going and records them rather than crashing.
    """

    site_id: PyObjectId
    start_time: datetime = Field(default_factory=utcnow)
    end_time: datetime | None = None
    tenders_found: int = 0
    tier_used: ScrapeTier | None = None
    errors: list[str] = Field(default_factory=list)

    @property
    def duration_seconds(self) -> float | None:
        """Wall-clock duration, or None if the run hasn't finished."""
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time).total_seconds()
