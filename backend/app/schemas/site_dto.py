"""Request/response schemas for the Sites API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import ContentType
from app.models.site_config import ExtractionRules, RateLimitConfig, SiteConfig
from app.models.types import HttpUrlStr


class SiteCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    base_url: HttpUrlStr
    content_type: ContentType | None = None  # auto-detected when omitted
    extraction_rules: ExtractionRules = Field(default_factory=ExtractionRules)
    rate_limit_config: RateLimitConfig = Field(default_factory=RateLimitConfig)
    locale: str | None = None
    timezone: str | None = None


class SiteUpdateRequest(BaseModel):
    name: str | None = None
    content_type: ContentType | None = None
    extraction_rules: ExtractionRules | None = None
    rate_limit_config: RateLimitConfig | None = None
    is_active: bool | None = None
    locale: str | None = None
    timezone: str | None = None


class SiteResponse(BaseModel):
    id: str
    name: str
    base_url: str
    content_type: ContentType
    extraction_rules: ExtractionRules
    rate_limit_config: RateLimitConfig
    is_active: bool
    locale: str | None
    timezone: str | None
    created_at: datetime

    @classmethod
    def from_site(cls, site: SiteConfig) -> "SiteResponse":
        return cls(
            id=str(site.id),
            name=site.name,
            base_url=site.base_url,
            content_type=site.content_type,
            extraction_rules=site.extraction_rules,
            rate_limit_config=site.rate_limit_config,
            is_active=site.is_active,
            locale=site.locale,
            timezone=site.timezone,
            created_at=site.created_at,
        )


class TenderPreview(BaseModel):
    """A single extracted tender in a dry-run preview (not persisted)."""

    title: str | None
    reference_number: str | None
    deadline: datetime | None
    estimated_budget: float | None
    currency: str
    status: str


class SiteTestResponse(BaseModel):
    count: int
    tenders: list[TenderPreview]
