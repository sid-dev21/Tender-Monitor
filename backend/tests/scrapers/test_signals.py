"""Phase 2 — escalation signal logic (pure functions, no I/O)."""

from __future__ import annotations

import pytest

from app.scrapers.fetch import signals

REAL_PAGE = "<html><body>" + ("<article>tender</article>" * 40) + "</body></html>"


@pytest.mark.parametrize("status", [403, 429, 503])
def test_block_statuses_escalate(status: int) -> None:
    escalate, reason = signals.should_escalate(status, {}, REAL_PAGE)
    assert escalate is True
    assert reason == f"block_status_{status}"


def test_cloudflare_body_marker_escalates() -> None:
    body = "<html><head><title>Just a moment...</title></head><body>checking</body></html>"
    escalate, reason = signals.should_escalate(200, {}, body)
    assert escalate is True
    assert reason == "cloudflare_challenge"


def test_cloudflare_header_marker_escalates() -> None:
    escalate, reason = signals.should_escalate(200, {"cf-ray": "abc123"}, REAL_PAGE)
    assert escalate is True
    assert reason == "cloudflare_challenge"


def test_empty_body_escalates() -> None:
    escalate, reason = signals.should_escalate(200, {}, "<html></html>")
    assert escalate is True
    assert reason == "empty_body"


def test_healthy_page_does_not_escalate() -> None:
    escalate, reason = signals.should_escalate(200, {"content-type": "text/html"}, REAL_PAGE)
    assert escalate is False
    assert reason is None
