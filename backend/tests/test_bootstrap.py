"""Phase 0 bootstrap tests — verify the skeleton works against real infrastructure."""

from __future__ import annotations

import httpx
import pytest
from httpx import ASGITransport


@pytest.mark.asyncio
async def test_settings_loads_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Settings should read values from the environment."""
    from app.core.config import Settings

    monkeypatch.setenv("ENV", "prod")
    monkeypatch.setenv("MONGO_DB", "custom_db")
    settings = Settings()

    assert settings.env == "prod"
    assert settings.is_prod is True
    assert settings.mongo_db == "custom_db"
    assert settings.notification_emails_max == 5


@pytest.mark.asyncio
async def test_health_returns_ok_when_mongo_up(db) -> None:  # noqa: ANN001
    """/health should report mongo 'up' against a real containerized MongoDB.

    The `db` fixture points the app at the test container and connects it, so the
    app's lifespan must NOT reconnect. We build the app without lifespan side effects
    by calling the router against the already-connected db module.
    """
    from app.api import health
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(health.router)

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["mongo"] == "up"
