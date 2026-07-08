"""API test fixtures: an httpx client wired to the real app + real test Mongo."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest_asyncio
from httpx import ASGITransport

from app.main import create_app


@pytest_asyncio.fixture
async def client(db) -> AsyncIterator[httpx.AsyncClient]:  # noqa: ANN001
    """AsyncClient against the full app. The `db` fixture connects the global db
    module to the test container, which get_db() reads — so no lifespan needed."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
