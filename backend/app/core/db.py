"""MongoDB connection management using pymongo's native AsyncMongoClient (NOT Motor).

The client is created once at application startup (via the FastAPI lifespan) and
exposed through module-level accessors. Repositories and services call get_db()
rather than creating their own clients.
"""

from __future__ import annotations

from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from app.core.config import get_settings
from app.core.logging import logger

_client: AsyncMongoClient | None = None
_db: AsyncDatabase | None = None


async def connect() -> None:
    """Open the MongoDB connection and verify it with a ping. Idempotent."""
    global _client, _db
    if _client is not None:
        return
    settings = get_settings()
    _client = AsyncMongoClient(settings.mongo_uri, tz_aware=True)
    _db = _client[settings.mongo_db]
    await _client.admin.command("ping")
    logger.info("Connected to MongoDB db={}", settings.mongo_db)


async def disconnect() -> None:
    """Close the MongoDB connection. Idempotent."""
    global _client, _db
    if _client is not None:
        await _client.close()
        logger.info("Disconnected from MongoDB")
    _client = None
    _db = None


def get_db() -> AsyncDatabase:
    """Return the active database handle. Raises if connect() has not run."""
    if _db is None:
        raise RuntimeError("Database not initialized. Call connect() first (via app lifespan).")
    return _db


async def ping() -> bool:
    """Ping the database; return True if reachable, False otherwise."""
    try:
        await get_db().command("ping")
        return True
    except Exception as exc:  # noqa: BLE001 - health check must never raise
        logger.warning("Mongo ping failed: {}", exc)
        return False
