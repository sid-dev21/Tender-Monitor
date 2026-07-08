"""FetchResult — the uniform return type of every fetch tier.

Whether a page was retrieved by httpx (Tier 1), Playwright (Tier 2), or stealth
(Tier 3), callers get the same shape back. The TierRouter inspects it to decide
whether to escalate, and the engines read `.html` to extract tenders.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.enums import ScrapeTier


@dataclass
class FetchResult:
    html: str
    status_code: int
    final_url: str
    tier_used: ScrapeTier
    headers: dict[str, str] = field(default_factory=dict)
    captcha_detected: bool = False
    error: str | None = None

    @property
    def ok(self) -> bool:
        """A clean 2xx response with no recorded error."""
        return 200 <= self.status_code < 300 and self.error is None
