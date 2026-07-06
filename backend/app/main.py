"""FastAPI application factory and ASGI entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.api import health
from app.core import db
from app.core.config import get_settings
from app.core.indexes import ensure_indexes
from app.core.logging import configure_logging, logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Open resources on startup, release them on shutdown."""
    configure_logging()
    await db.connect()
    await ensure_indexes(db.get_db())
    logger.info("Tender Monitor started (env={})", get_settings().env)
    try:
        yield
    finally:
        await db.disconnect()
        logger.info("Tender Monitor stopped")


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = get_settings()
    app = FastAPI(
        title="Tender Monitor API",
        version="0.1.0",
        description="Config-driven web scraping SaaS for Burkina Faso public tenders (BTP).",
        lifespan=lifespan,
        debug=not settings.is_prod,
    )
    app.include_router(health.router)
    return app


app = create_app()
