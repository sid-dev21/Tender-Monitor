"""Escalation signals — pure functions that decide when to step up a fetch tier.

Kept free of any I/O so they are trivially testable. The TierRouter feeds a
response's status/headers/body in and gets back a (should_escalate, reason) pair.
"""

from __future__ import annotations

# Statuses that typically mean "blocked / rate-limited / challenged".
BLOCK_STATUSES = frozenset({403, 429, 503})

# Substrings that betray a Cloudflare (or similar) interstitial challenge page.
CLOUDFLARE_MARKERS = (
    "just a moment",
    "attention required",
    "cf-browser-verification",
    "challenge-platform",
    "__cf_chl",
    "cf-ray",
    "enable javascript and cookies to continue",
)

# Below this, an HTML response is suspiciously empty (likely JS-rendered or blocked).
MIN_HTML_LENGTH = 500


def is_block_status(status_code: int) -> bool:
    return status_code in BLOCK_STATUSES


def has_cloudflare_markers(headers: dict[str, str], body: str) -> bool:
    """True if Cloudflare challenge fingerprints appear in headers or body."""
    header_blob = " ".join(f"{k}:{v}" for k, v in headers.items()).lower()
    body_lower = body[:4000].lower()  # only the head of the doc matters
    return any(m in header_blob or m in body_lower for m in CLOUDFLARE_MARKERS)


def is_body_too_short(body: str, min_length: int = MIN_HTML_LENGTH) -> bool:
    """True if the body is too small to plausibly contain real content."""
    return len(body.strip()) < min_length


def should_escalate(
    status_code: int, headers: dict[str, str], body: str
) -> tuple[bool, str | None]:
    """Decide whether the current tier's response warrants escalation.

    Returns (escalate, reason). `reason` is a short tag for logging / ScraperRun.
    """
    if is_block_status(status_code):
        return True, f"block_status_{status_code}"
    if has_cloudflare_markers(headers, body):
        return True, "cloudflare_challenge"
    if is_body_too_short(body):
        return True, "empty_body"
    return False, None
