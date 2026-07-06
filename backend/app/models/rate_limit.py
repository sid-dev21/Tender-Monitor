"""DomainRateLimitState — persisted per-domain scraping state.

Kept in Mongo (not memory) so politeness, backoff, tier memory, and the daily cap
all survive process restarts. One document per domain (unique `domain` index).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.models.base import MongoModel
from app.models.enums import ScrapeTier


class DomainRateLimitState(MongoModel):
    """Adaptive rate-limit + tier state for a single domain (e.g. 'arcop.bf')."""

    domain: str

    # --- Adaptive delay (Phase 4) ---
    current_delay_ms: int = 5000              # grows on 429/errors, shrinks on success
    consecutive_successes: int = 0            # drives gradual recovery
    blocked_until: datetime | None = None     # set on 429 (honours Retry-After)
    last_request_at: datetime | None = None

    # --- Daily cap (Phase 4) ---
    requests_today: int = 0
    # ISO date string ("YYYY-MM-DD") of when requests_today was last reset.
    # A string, not a date, because BSON has no native date-only type.
    requests_reset_date: str | None = None

    # --- Tier memory (Phase 2) ---
    # The last fetch tier that successfully retrieved this domain, so the router
    # can start there next time instead of re-escalating from scratch.
    last_working_tier: ScrapeTier | None = None
