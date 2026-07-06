"""SiteConfig — the document that turns 'a site' into pure configuration data.

This is the heart of the architecture: adding a new source to scrape means
inserting one of these documents. No Python code is written per site. The two
generic engines (HTMLScraper, PDFScraper) read these rules and act accordingly.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from app.models.base import MongoModel
from app.models.enums import ContentType
from app.models.objectid import PyObjectId
from app.models.types import HttpUrlStr

# Default used by PDFScraper when a site provides no PDF-discovery rule:
# "every link whose URL ends in .pdf".
DEFAULT_PDF_LINK_SELECTOR = 'a[href$=".pdf"]'


class ExtractionRules(BaseModel):
    """How to pull tender fields out of a page or PDF.

    HTML sites use `list_selector` + the per-field CSS selectors. PDF sites use
    `pdf_link_selector` or `pdf_url_pattern` to find documents. Every selector is
    optional — `regex_fallback_enabled` lets the field parser fill any gaps.
    """

    # --- HTML extraction (CSS selectors) ---
    list_selector: str | None = None       # selects each tender block on the page
    title_selector: str | None = None
    reference_selector: str | None = None
    date_selector: str | None = None
    deadline_selector: str | None = None
    budget_selector: str | None = None
    authority_selector: str | None = None

    # --- PDF discovery ---
    pdf_link_selector: str | None = None    # CSS selector for <a> links to PDFs
    pdf_url_pattern: str | None = None      # regex to match PDF URLs on the page

    # When a selector misses, fall back to the French-procurement regex parser.
    regex_fallback_enabled: bool = True


class RateLimitConfig(BaseModel):
    """Per-site politeness settings, consumed by the adaptive rate limiter."""

    min_delay_ms: int = Field(default=3000, ge=0)
    max_delay_ms: int = Field(default=8000, ge=0)
    daily_cap: int = Field(default=200, ge=1)

    @model_validator(mode="after")
    def _check_delay_order(self) -> RateLimitConfig:
        if self.max_delay_ms < self.min_delay_ms:
            raise ValueError("max_delay_ms must be >= min_delay_ms")
        return self


class SiteConfig(MongoModel):
    """A user-owned scraping source, stored in the `site_configs` collection."""

    name: str = Field(min_length=1)
    base_url: HttpUrlStr
    content_type: ContentType
    extraction_rules: ExtractionRules = Field(default_factory=ExtractionRules)
    rate_limit_config: RateLimitConfig = Field(default_factory=RateLimitConfig)
    is_active: bool = True
    created_by_user_id: PyObjectId

    # NOTE: selectors are intentionally NOT required here. The minimal way to add a
    # site is name + base_url + content_type (content_type itself is auto-detected
    # at the API layer). The engines apply smart fallbacks when rules are empty:
    #   - PDF with no pdf rule  -> DEFAULT_PDF_LINK_SELECTOR ("all .pdf links")
    #   - HTML with no list_selector -> parse the whole page via the regex parser
    # Users only add selectors later to sharpen extraction, guided by /sites/{id}/test.

    def effective_pdf_link_selector(self) -> str:
        """The PDF-discovery selector to actually use, falling back to the default."""
        return self.extraction_rules.pdf_link_selector or DEFAULT_PDF_LINK_SELECTOR
