"""Shared test fixtures.

Testing philosophy: NO MOCKS for external systems.
- MongoDB: a real container via testcontainers, one per test session.
- HTTP: vcrpy cassettes (recorded once, replayed after) under tests/fixtures/cassettes/.
- Fixtures: real HTML/PDF files under tests/fixtures/.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Callable, Iterator
from pathlib import Path

import pytest
import pytest_asyncio
from pymongo import AsyncMongoClient
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
