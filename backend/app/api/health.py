"""Health and readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.core import db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness + Mongo connectivity check."""
    mongo_up = await db.ping()
    return {"status": "ok", "mongo": "up" if mongo_up else "down"}
