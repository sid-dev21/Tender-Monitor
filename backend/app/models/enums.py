"""Closed vocabularies shared across models.

Using str-enums means Mongo stores readable values ("html", "pdf") AND any invalid
value is rejected at validation time instead of silently corrupting data.
"""

from __future__ import annotations

from enum import IntEnum, StrEnum


class ContentType(StrEnum):
    """Which generic engine handles a site."""

    HTML = "html"
    PDF = "pdf"


class TenderStatus(StrEnum):
    """Extraction confidence outcome for a tender."""

    PARSED = "parsed"          # >= 4 fields extracted
    NEEDS_REVIEW = "needs_review"  # < 4 fields; a human should check


class ScrapeTier(IntEnum):
    """Which fetch tier successfully retrieved the page."""

    HTTPX = 1
    PLAYWRIGHT = 2
    STEALTH = 3


class NotificationFrequency(StrEnum):
    """How often a user's tender report is sent."""

    DAILY = "daily"
    WEEKLY = "weekly"
