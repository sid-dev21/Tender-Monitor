"""Fixtures for scraper tests: a real local HTTP server (no mocks, no network).

Spins up a stdlib HTTP server on a random localhost port so fetch tiers can make
genuine HTTP requests against controllable responses — deterministic and offline.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

# path -> (status_code, body, headers)
Route = tuple[int, str, dict[str, str]]


class _RoutedServer(ThreadingHTTPServer):
    routes: dict[str, Route]
    gated: dict[str, str]  # path -> body; served only to real-browser requests

    def __init__(self, addr: tuple[str, int], handler: type[BaseHTTPRequestHandler]) -> None:
        super().__init__(addr, handler)
        self.routes = {}
        self.gated = {}


class _Handler(BaseHTTPRequestHandler):
    def _respond(self, status: int, body: str, headers: dict[str, str]) -> None:
        self.send_response(status)
        for key, value in headers.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def _is_real_browser(self) -> bool:
        """Chromium sends Sec-Fetch-* / sec-ch-ua headers; httpx does not."""
        return bool(
            self.headers.get("Sec-Fetch-Mode") or self.headers.get("sec-ch-ua")
        )

    def do_GET(self) -> None:  # noqa: N802 - required name by BaseHTTPRequestHandler
        server: _RoutedServer = self.server  # type: ignore[assignment]
        html = {"Content-Type": "text/html; charset=utf-8"}

        # Browser-gated: 403 to raw HTTP (Tier 1), 200 to a real browser (Tier 2/3).
        if self.path in server.gated:
            if self._is_real_browser():
                self._respond(200, server.gated[self.path], html)
            else:
                self._respond(403, "<html><body>Forbidden</body></html>", html)
            return

        entry = server.routes.get(self.path)
        if entry is None:
            self._respond(404, "not found", html)
            return
        status, body, headers = entry
        self._respond(status, body, headers)

    def log_message(self, *args: object) -> None:  # silence per-request logging
        pass


class LocalServer:
    """Handle returned to tests: register routes and read the base URL."""

    def __init__(self, server: _RoutedServer, base_url: str) -> None:
        self._server = server
        self.base_url = base_url

    def add(
        self, path: str, body: str, *, status: int = 200, headers: dict[str, str] | None = None
    ) -> str:
        self._server.routes[path] = (
            status,
            body,
            headers or {"Content-Type": "text/html; charset=utf-8"},
        )
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
