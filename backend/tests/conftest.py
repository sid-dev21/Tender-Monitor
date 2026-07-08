"""Shared test fixtures.

Testing philosophy: NO MOCKS for external systems.
- MongoDB: a real container via testcontainers, one per test session.
- HTTP: vcrpy cassettes (recorded once, replayed after) under tests/fixtures/cassettes/.
- Fixtures: real HTML/PDF files under tests/fixtures/.
"""

from __future__ import annotations

import os
import threading
import time
from collections.abc import AsyncIterator, Callable, Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from pymongo import AsyncMongoClient
from testcontainers.core.container import DockerContainer
from testcontainers.mongodb import MongoDbContainer

FIXTURES_DIR = Path(__file__).parent / "fixtures"
CASSETTES_DIR = FIXTURES_DIR / "cassettes"


# --------------------------------------------------------------------------- #
# MongoDB (real container, session-scoped)
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="session")
def mongo_container() -> Iterator[MongoDbContainer]:
    """Spin up a real MongoDB container for the whole test session."""
    with MongoDbContainer("mongo:7") as container:
        yield container


@pytest.fixture(scope="session")
def mongo_uri(mongo_container: MongoDbContainer) -> str:
    return mongo_container.get_connection_url()


@pytest_asyncio.fixture
async def db(mongo_uri: str) -> AsyncIterator:
    """Function-scoped clean database.

    Points the app's db module at the test container, connects, and drops all
    collections after each test so tests never leak state into each other.
    """
    # Route the app's global db module at the container before importing users of it.
    os.environ["MONGO_URI"] = mongo_uri
    os.environ["MONGO_DB"] = "test_tender_monitor"

    from app.core.config import get_settings
    from app.core import db as db_module

    get_settings.cache_clear()  # settings are lru_cached; pick up the test env
    await db_module.disconnect()
    await db_module.connect()
    database = db_module.get_db()

    # Clean slate before the test, then create the same indexes as production
    # (dropping collections also drops their indexes, so recreate them here).
    for name in await database.list_collection_names():
        await database.drop_collection(name)

    from app.core.indexes import ensure_indexes

    await ensure_indexes(database)

    yield database

    # Clean up after the test.
    for name in await database.list_collection_names():
        await database.drop_collection(name)
    await db_module.disconnect()


# --------------------------------------------------------------------------- #
# VCR (HTTP record/replay)
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def vcr_config() -> dict:
    """Global VCR configuration for pytest-vcr."""
    return {
        "cassette_library_dir": str(CASSETTES_DIR),
        "record_mode": "once",  # record on first run, replay after
        "match_on": ["method", "scheme", "host", "port", "path", "query"],
        "filter_headers": ["authorization", "cookie", "user-agent"],
        "decode_compressed_response": True,
    }


# --------------------------------------------------------------------------- #
# Fixture path helpers
# --------------------------------------------------------------------------- #
@pytest.fixture
def html_fixture() -> Callable[[str], str]:
    """Return a loader that reads a real HTML fixture by filename."""

    def _load(name: str) -> str:
        return (FIXTURES_DIR / "html" / name).read_text(encoding="utf-8")

    return _load


@pytest.fixture
def pdf_fixture() -> Callable[[str], bytes]:
    """Return a loader that reads a real PDF fixture by filename (as bytes)."""

    def _load(name: str) -> bytes:
        return (FIXTURES_DIR / "pdfs" / name).read_bytes()

    return _load


# --------------------------------------------------------------------------- #
# Local HTTP server (real sockets, no network, no mocks)
# --------------------------------------------------------------------------- #
class _RoutedServer(ThreadingHTTPServer):
    def __init__(self, addr: tuple[str, int], handler: type[BaseHTTPRequestHandler]) -> None:
        super().__init__(addr, handler)
        self.routes: dict[str, tuple[int, str, dict[str, str]]] = {}
        self.raw: dict[str, tuple[bytes, str]] = {}  # path -> (bytes, content_type)
        self.gated: dict[str, str] = {}              # path -> body (real-browser only)


class _Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: bytes, headers: dict[str, str]) -> None:
        self.send_response(status)
        for key, value in headers.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def _is_real_browser(self) -> bool:
        return bool(self.headers.get("Sec-Fetch-Mode") or self.headers.get("sec-ch-ua"))

    def do_GET(self) -> None:  # noqa: N802
        server: _RoutedServer = self.server  # type: ignore[assignment]
        html = {"Content-Type": "text/html; charset=utf-8"}

        if self.path in server.raw:
            data, ctype = server.raw[self.path]
            self._send(200, data, {"Content-Type": ctype})
            return
        if self.path in server.gated:
            if self._is_real_browser():
                self._send(200, server.gated[self.path].encode("utf-8"), html)
            else:
                self._send(403, b"<html><body>Forbidden</body></html>", html)
            return
        entry = server.routes.get(self.path)
        if entry is None:
            self._send(404, b"not found", html)
            return
        status, body, headers = entry
        self._send(status, body.encode("utf-8"), headers)

    def log_message(self, *args: object) -> None:
        pass


class LocalServer:
    """Register routes and read the base URL. Serves real HTTP over a real socket."""

    def __init__(self, server: _RoutedServer, base_url: str) -> None:
        self._server = server
        self.base_url = base_url

    def add(
        self, path: str, body: str, *, status: int = 200, headers: dict[str, str] | None = None
    ) -> str:
        self._server.routes[path] = (
            status, body, headers or {"Content-Type": "text/html; charset=utf-8"}
        )
        return f"{self.base_url}{path}"

    def add_bytes(self, path: str, data: bytes, *, content_type: str = "application/pdf") -> str:
        self._server.raw[path] = (data, content_type)
        return f"{self.base_url}{path}"

    def add_browser_gated(self, path: str, body: str) -> str:
        """A route that 403s raw HTTP but serves `body` to a real browser."""
        self._server.gated[path] = body
        return f"{self.base_url}{path}"


@pytest.fixture
def http_server() -> Iterator[LocalServer]:
    server = _RoutedServer(("127.0.0.1", 0), _Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield LocalServer(server, f"http://127.0.0.1:{port}")
    finally:
        server.shutdown()
        server.server_close()


# --------------------------------------------------------------------------- #
# MailHog (real SMTP catcher) — for email notification tests
# --------------------------------------------------------------------------- #
@pytest.fixture
def mailhog() -> Iterator[str]:
    """Start MailHog, point SMTP settings at it, and yield its HTTP API base URL."""
    from app.core.config import get_settings

    container = DockerContainer("mailhog/mailhog:latest")
    container.with_exposed_ports(1025, 8025)
    container.start()
    try:
        host = container.get_container_host_ip()
        smtp_port = container.get_exposed_port(1025)
        http_port = container.get_exposed_port(8025)
        api_base = f"http://{host}:{http_port}"

        # Wait until the HTTP API answers.
        for _ in range(40):
            try:
                if httpx.get(f"{api_base}/api/v2/messages", timeout=1).status_code == 200:
                    break
            except Exception:  # noqa: BLE001
                pass
            time.sleep(0.5)

        os.environ["SMTP_HOST"] = host
        os.environ["SMTP_PORT"] = str(smtp_port)
        os.environ["SMTP_USE_TLS"] = "false"
        os.environ["SMTP_USERNAME"] = ""
        os.environ["SMTP_PASSWORD"] = ""
        get_settings.cache_clear()
        yield api_base
    finally:
        for key in ("SMTP_HOST", "SMTP_PORT", "SMTP_USE_TLS"):
            os.environ.pop(key, None)
        get_settings.cache_clear()
        container.stop()
