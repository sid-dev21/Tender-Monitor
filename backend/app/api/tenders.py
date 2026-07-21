"""Tenders API: browse and keyword-filter extracted tenders."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pymongo.asynchronous.database import AsyncDatabase

from app.core.config import get_settings
from app.dependencies.deps import get_current_user, get_db
from app.models.user import User
from app.repositories.tender_repo import TenderRepo
from app.schemas.tender_dto import TenderResponse
from app.services.keyword_matcher import filter_tenders, matched_keywords
from app.services.keyword_normalizer import normalize_list
from app.services.relevance_scorer import score_tender

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


@router.post("/score", response_model=list[TenderResponse])
async def score_my_tenders(
    keywords: str | None = Query(default=None, description="Comma-separated keywords"),
    current: User = Depends(get_current_user),
    db: AsyncDatabase = Depends(get_db),
) -> list[TenderResponse]:
    """On-demand semantic relevance scoring (local LLM via Ollama).

    Scores the current user's keyword-matched tenders against their free-text
    company profile, capped to `settings.score_max_tenders` to bound latency
    (each tender is one LLM call, run sequentially — Ollama serves one request
    at a time per model anyway). Explicit, user-triggered action; never runs
    automatically. See app/services/relevance_scorer.py.
    """
    settings = get_settings()
    kws = normalize_list(keywords.split(",")) if keywords else current.keywords
    tenders = await _recent(db)
    filtered = filter_tenders(tenders, kws) if kws else tenders
    subset = filtered[: settings.score_max_tenders]

    scored: list[TenderResponse] = []
    for t in subset:
        relevance = await score_tender(current.company_profile, t)
        scored.append(
            TenderResponse.from_tender(
                t,
                matched_keywords(t, kws),
                relevance_label=relevance.label,
                relevance_score=relevance.score,
                relevance_reason=relevance.reason,
            )
        )
    scored.sort(key=lambda r: r.relevance_score or 0, reverse=True)
    return scored
