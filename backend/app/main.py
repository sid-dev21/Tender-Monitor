"""FastAPI application factory and ASGI entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import (
    auth,
    health,
    notification_schedule,
    notifications,
    sites,
    tenders,
    users,
)
from app.core import db
from app.core.config import FRONTEND_DIST, frontend_is_bundled, get_settings
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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=settings.cors_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(sites.router)
    app.include_router(tenders.router)
    app.include_router(notifications.router)
    app.include_router(notification_schedule.router)
    _mount_frontend(app)
    return app


def _mount_frontend(app: FastAPI) -> None:
    """Serve the built React app from this same server, when it exists.

    Single-origin deployment: with the SPA and the API behind one URL, there is
    no CORS to configure and no API base URL to bake into the build — which is
    what makes exposing the whole app through one tunnel (or one container)
    practical. In development the Vite dev server is used instead and this
    directory simply does not exist, so nothing is mounted.

    Registered last, so /api/* and /docs always win over the catch-all.
    """
    if not frontend_is_bundled():
        logger.info("No built frontend at {} — serving API only", FRONTEND_DIST)
        return

    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str) -> FileResponse:
        """Return the requested file, else index.html so client-side routing works.

        A deep link like /reset-password?token=… has no file on disk; the router
        resolves it in the browser, so index.html must be served for it.
        """
        candidate = (FRONTEND_DIST / full_path).resolve()
        if full_path and candidate.is_file() and candidate.is_relative_to(FRONTEND_DIST):
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")

    logger.info("Serving built frontend from {}", FRONTEND_DIST)


app = create_app()
