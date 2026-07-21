"""User self-service endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pymongo.asynchronous.database import AsyncDatabase

from app.core.config import get_settings
from app.dependencies.deps import get_current_user, get_db
from app.models.user import User
from app.repositories.user_repo import UserRepo
from app.schemas.auth_dto import CompanyProfileUpdate, UserResponse
from app.schemas.notification_dto import NotificationEmailsUpdate
from app.schemas.tender_dto import KeywordsUpdateRequest
from app.services.keyword_normalizer import normalize_list

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def me(current: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.from_user(current)


@router.patch("/me/keywords", response_model=UserResponse)
async def update_keywords(
    body: KeywordsUpdateRequest,
    current: User = Depends(get_current_user),
    db: AsyncDatabase = Depends(get_db),
) -> UserResponse:
    """Replace the user's keywords (normalized: lowercased, accent-stripped, deduped)."""
    keywords = normalize_list(body.keywords, max_items=get_settings().keywords_max_per_user)
    updated = await UserRepo(db).update_by_id(current.id, {"keywords": keywords})
    assert updated is not None
    return UserResponse.from_user(updated)


@router.patch("/me/profile", response_model=UserResponse)
async def update_company_profile(
    body: CompanyProfileUpdate,
    current: User = Depends(get_current_user),
    db: AsyncDatabase = Depends(get_db),
) -> UserResponse:
    """Set the free-text company profile used as context for LLM relevance scoring."""
    updated = await UserRepo(db).update_by_id(
        current.id, {"company_profile": body.company_profile.strip() or None}
    )
    assert updated is not None
    return UserResponse.from_user(updated)


@router.patch("/me/notification-emails", response_model=UserResponse)
async def update_notification_emails(
    body: NotificationEmailsUpdate,
    current: User = Depends(get_current_user),
    db: AsyncDatabase = Depends(get_db),
) -> UserResponse:
    """Set recipient emails for reports (max 5, enforced by the schema)."""
    emails = [str(e) for e in body.emails]
    updated = await UserRepo(db).update_by_id(current.id, {"notification_emails": emails})
    assert updated is not None
    return UserResponse.from_user(updated)
