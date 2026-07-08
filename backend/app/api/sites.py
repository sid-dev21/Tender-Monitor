"""Sites API: users manage their scraping sources (CRUD + auto-detect + dry-run)."""

from __future__ import annotations

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.asynchronous.database import AsyncDatabase

from app.dependencies.deps import get_current_user, get_db
from app.models.site_config import SiteConfig
from app.models.user import User
from app.repositories.site_config_repo import SiteConfigRepo
from app.schemas.site_dto import (
    SiteCreateRequest,
    SiteResponse,
    SiteTestResponse,
    SiteUpdateRequest,
    TenderPreview,
)
from app.scrapers.orchestrator import run_scrape
from app.services.content_type_detector import detect_content_type

router = APIRouter(prefix="/api/sites", tags=["sites"])


async def _owned_site(site_id: str, user: User, db: AsyncDatabase) -> SiteConfig:
    """Load a site and ensure the caller owns it (404 otherwise, no info leak)."""
    if not ObjectId.is_valid(site_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Site not found")
    site = await SiteConfigRepo(db).find_by_id(site_id)
    if site is None or site.created_by_user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Site not found")
    return site


@router.post("", response_model=SiteResponse, status_code=status.HTTP_201_CREATED)
async def create_site(
    body: SiteCreateRequest,
    current: User = Depends(get_current_user),
    db: AsyncDatabase = Depends(get_db),
) -> SiteResponse:
    content_type = body.content_type or await detect_content_type(body.base_url)
    site = SiteConfig(
        name=body.name,
        base_url=body.base_url,
        content_type=content_type,
        extraction_rules=body.extraction_rules,
        rate_limit_config=body.rate_limit_config,
        locale=body.locale,
        timezone=body.timezone,
        created_by_user_id=current.id,
    )
    saved = await SiteConfigRepo(db).insert(site)
    return SiteResponse.from_site(saved)


@router.get("", response_model=list[SiteResponse])
async def list_sites(
    current: User = Depends(get_current_user),
    db: AsyncDatabase = Depends(get_db),
) -> list[SiteResponse]:
    sites = await SiteConfigRepo(db).find_by_user(current.id)
    return [SiteResponse.from_site(s) for s in sites]


@router.get("/{site_id}", response_model=SiteResponse)
async def get_site(
    site_id: str,
    current: User = Depends(get_current_user),
    db: AsyncDatabase = Depends(get_db),
) -> SiteResponse:
    return SiteResponse.from_site(await _owned_site(site_id, current, db))


@router.patch("/{site_id}", response_model=SiteResponse)
async def update_site(
    site_id: str,
    body: SiteUpdateRequest,
    current: User = Depends(get_current_user),
    db: AsyncDatabase = Depends(get_db),
) -> SiteResponse:
    await _owned_site(site_id, current, db)
    changes = body.model_dump(exclude_none=True)
    updated = await SiteConfigRepo(db).update_by_id(site_id, changes)
    assert updated is not None
    return SiteResponse.from_site(updated)


@router.delete("/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_site(
    site_id: str,
    current: User = Depends(get_current_user),
    db: AsyncDatabase = Depends(get_db),
) -> None:
    await _owned_site(site_id, current, db)
    await SiteConfigRepo(db).delete_by_id(site_id)


@router.post("/{site_id}/test", response_model=SiteTestResponse)
async def test_site(
    site_id: str,
    current: User = Depends(get_current_user),
    db: AsyncDatabase = Depends(get_db),
) -> SiteTestResponse:
    """Dry-run scrape: preview extracted tenders WITHOUT saving them."""
    await _owned_site(site_id, current, db)
    result = await run_scrape(site_id, db, dry_run=True)
    previews = [
        TenderPreview(
            title=t.title,
            reference_number=t.reference_number,
            deadline=t.deadline,
            estimated_budget=t.estimated_budget,
            currency=t.currency,
            status=t.status.value,
        )
        for t in result.tenders
    ]
    return SiteTestResponse(count=len(previews), tenders=previews)
