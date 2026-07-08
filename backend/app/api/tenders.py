"""Tenders API: browse and keyword-filter extracted tenders."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pymongo.asynchronous.database import AsyncDatabase

from app.dependencies.deps import get_current_user, get_db
from app.models.user import User
from app.repositories.tender_repo import TenderRepo
from app.schemas.tender_dto import TenderResponse
from app.services.keyword_matcher import filter_tenders, matched_keywords
from app.services.keyword_normalizer import normalize_list

router = APIRouter(prefix="/api/tenders", tags=["tenders"])

# Cap how many recent tenders we scan for keyword matching (MVP scale).
_SCAN_LIMIT = 500


async def _recent(db: AsyncDatabase) -> list:
    return await TenderRepo(db).find({}, limit=_SCAN_LIMIT, sort=[("created_at", -1)])


@router.get("", response_model=list[TenderResponse])
async def list_tenders(
    keywords: str | None = Query(default=None, description="Comma-separated keywords"),
    limit: int = Query(default=100, le=_SCAN_LIMIT),
    _current: User = Depends(get_current_user),
    db: AsyncDatabase = Depends(get_db),
) -> list[TenderResponse]:
    kws = normalize_list(keywords.split(",")) if keywords else []
    tenders = await _recent(db)
    filtered = filter_tenders(tenders, kws)[:limit]
    return [TenderResponse.from_tender(t, matched_keywords(t, kws)) for t in filtered]


@router.get("/mine", response_model=list[TenderResponse])
async def my_tenders(
    limit: int = Query(default=100, le=_SCAN_LIMIT),
    current: User = Depends(get_current_user),
    db: AsyncDatabase = Depends(get_db),
) -> list[TenderResponse]:
    """Tenders matching the current user's saved keywords (all recent if none set)."""
    kws = current.keywords  # already normalized at save time
    tenders = await _recent(db)
    filtered = filter_tenders(tenders, kws)[:limit] if kws else tenders[:limit]
    return [TenderResponse.from_tender(t, matched_keywords(t, kws)) for t in filtered]
