"""LLM relevance scoring — real local HTTP server standing in for Ollama.

No mocks: a real local HTTP server (real socket, real POST handling) plays the
role of Ollama's `/api/chat` endpoint, exactly like tests/scrapers/test_tier1_httpx.py
does for real sites. No MongoDB needed — score_tender() is pure HTTP + parsing.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from bson import ObjectId

from app.core.config import get_settings
from app.models.enums import ContentType
from app.models.tender import Tender
from app.services.relevance_scorer import clear_cache, score_tender


@pytest.fixture(autouse=True)
def _clean_cache() -> Iterator[None]:
    """Verdicts are memoized process-wide; isolate every test from the others."""
    clear_cache()
    yield
    clear_cache()


def _make_tender(**overrides: object) -> Tender:
    defaults: dict[str, object] = dict(
        title="Construction d'une route bitumée à Ouagadougou",
        reference_number="AOO-2026-001",
        source_site_id=ObjectId(),
        extraction_type=ContentType.HTML,
        raw_text=(
            "Travaux de construction d'une route bitumée de 12km, "
            "lot voirie et assainissement."
        ),
    )
    defaults.update(overrides)
    return Tender(**defaults)  # type: ignore[arg-type]


class _OllamaChatHandler(BaseHTTPRequestHandler):
    """Fakes just enough of Ollama's POST /api/chat to exercise score_tender()."""

    response_body: bytes = b""
    status_code: int = 200

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)  # drain the request body (not asserted on here)
        self.send_response(type(self).status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(type(self).response_body)

    def log_message(self, *args: object) -> None:  # silence test output
        pass


@pytest.fixture
def ollama_server() -> Iterator[tuple[str, type[_OllamaChatHandler]]]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _OllamaChatHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}", _OllamaChatHandler
    finally:
        server.shutdown()
        server.server_close()


def _point_at_ollama(monkeypatch: pytest.MonkeyPatch, host: str) -> None:
    monkeypatch.setenv("OLLAMA_HOST", host)
    get_settings.cache_clear()


async def test_score_tender_parses_valid_json_response(
    monkeypatch: pytest.MonkeyPatch,
    ollama_server: tuple[str, type[_OllamaChatHandler]],
) -> None:
    base_url, handler = ollama_server
    handler.response_body = json.dumps(
        {
            "message": {
                "content": json.dumps(
                    {"verdict": "correspond", "reason": "Correspond au profil BTP."}
                )
            }
        }
    ).encode()
    _point_at_ollama(monkeypatch, base_url)

    result = await score_tender(
        "Entreprise de BTP, spécialisée en voirie et routes", _make_tender()
    )

    assert result.label == "correspond"
    assert result.score == 90  # top band, used for ranking only
    assert result.reason == "Correspond au profil BTP."


async def test_verdicts_map_to_distinct_score_bands(
    monkeypatch: pytest.MonkeyPatch,
    ollama_server: tuple[str, type[_OllamaChatHandler]],
) -> None:
    """The whole point of the classify-then-map design: the three verdicts must
    come out ordered, so the tender list ranks sensibly."""
    base_url, handler = ollama_server
    _point_at_ollama(monkeypatch, base_url)

    scores = {}
    for verdict in ("correspond", "connexe", "hors_metier"):
        handler.response_body = json.dumps(
            {"message": {"content": json.dumps({"verdict": verdict, "reason": "r"})}}
        ).encode()
        scores[verdict] = (await score_tender("profil BTP", _make_tender())).score

    assert scores["correspond"] > scores["connexe"] > scores["hors_metier"]


async def test_unknown_verdict_does_not_invent_a_score(
    monkeypatch: pytest.MonkeyPatch,
    ollama_server: tuple[str, type[_OllamaChatHandler]],
) -> None:
    """The enum should prevent this, but if a model ever answers off-menu we
    report failure rather than guessing a number."""
    base_url, handler = ollama_server
    handler.response_body = json.dumps(
        {"message": {"content": json.dumps({"verdict": "peut-etre", "reason": "r"})}}
    ).encode()
    _point_at_ollama(monkeypatch, base_url)

    result = await score_tender("profil", _make_tender())

    assert result.label == "indisponible"
    assert result.score == 0
    assert result.reason


async def test_score_tender_falls_back_on_malformed_json(
    monkeypatch: pytest.MonkeyPatch,
    ollama_server: tuple[str, type[_OllamaChatHandler]],
) -> None:
    base_url, handler = ollama_server
    handler.response_body = json.dumps({"message": {"content": "ceci n'est pas du JSON"}}).encode()
    _point_at_ollama(monkeypatch, base_url)

    result = await score_tender("Entreprise de BTP", _make_tender())

    assert result.label == "indisponible"
    assert result.score == 0
    assert result.reason  # non-empty, explains the failure


async def test_score_tender_falls_back_when_ollama_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _point_at_ollama(monkeypatch, "http://127.0.0.1:1")  # nothing listens here

    result = await score_tender("Entreprise de BTP", _make_tender())

    assert result.label == "indisponible"
    assert result.score == 0
    assert result.reason


async def test_identical_tender_and_profile_is_scored_only_once(
    monkeypatch: pytest.MonkeyPatch,
    ollama_server: tuple[str, type[_OllamaChatHandler]],
) -> None:
    """The cache is what makes the feature usable: ~10s of CPU inference per
    tender must not be paid again for a pair already judged."""
    base_url, handler = ollama_server
    _point_at_ollama(monkeypatch, base_url)
    tender = _make_tender(id=ObjectId())  # only persisted tenders are cached

    handler.response_body = json.dumps(
        {"message": {"content": json.dumps({"verdict": "correspond", "reason": "premier"})}}
    ).encode()
    first = await score_tender("profil BTP", tender)

    # Change what the server would answer: a second inference would be visible.
    handler.response_body = json.dumps(
        {"message": {"content": json.dumps({"verdict": "hors_metier", "reason": "second"})}}
    ).encode()
    second = await score_tender("profil BTP", tender)

    assert second == first  # served from cache, no second call

    # A different profile is a different question, so it must be re-evaluated.
    third = await score_tender("profil totalement différent", tender)
    assert third.label == "hors_metier"


async def test_missing_reason_still_yields_a_score(
    monkeypatch: pytest.MonkeyPatch,
    ollama_server: tuple[str, type[_OllamaChatHandler]],
) -> None:
    """A verdict without justification is usable — don't discard the ranking."""
    base_url, handler = ollama_server
    handler.response_body = json.dumps(
        {"message": {"content": json.dumps({"verdict": "hors_metier"})}}
    ).encode()
    _point_at_ollama(monkeypatch, base_url)

    result = await score_tender("profil", _make_tender())

    assert result.label == "hors_metier"
    assert result.score == 10
    assert result.reason  # a placeholder sentence, never empty
