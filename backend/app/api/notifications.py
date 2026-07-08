"""Notifications API: in-app inbox, mark-seen, and manual send-now trigger."""

from __future__ import annotations

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.asynchronous.database import AsyncDatabase

from app.dependencies.deps import get_current_user, get_db
from app.models.user import User
from app.repositories.notification_repo import InAppNotificationRepo
from app.schemas.notification_dto import InAppNotificationResponse, SendNowResponse
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=list[InAppNotificationResponse])
async def list_notifications(
    unseen_only: bool = False,
    current: User = Depends(get_current_user),
    db: AsyncDatabase = Depends(get_db),
) -> list[InAppNotificationResponse]:
    items = await InAppNotificationRepo(db).find_for_user(current.id, unseen_only=unseen_only)
    return [InAppNotificationResponse.from_notification(n) for n in items]


@router.patch("/{notification_id}/mark-seen", response_model=InAppNotificationResponse)
async def mark_seen(
    notification_id: str,
    current: User = Depends(get_current_user),
    db: AsyncDatabase = Depends(get_db),
) -> InAppNotificationResponse:
    repo = InAppNotificationRepo(db)
    if not ObjectId.is_valid(notification_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification not found")
    existing = await repo.find_by_id(notification_id)
    if existing is None or existing.user_id != current.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification not found")
    updated = await repo.mark_seen(notification_id)
    assert updated is not None
    return InAppNotificationResponse.from_notification(updated)


@router.post("/send-now", response_model=SendNowResponse)
async def send_now(
    current: User = Depends(get_current_user),
    db: AsyncDatabase = Depends(get_db),
) -> SendNowResponse:
    """Build and deliver this user's report immediately (in-app + email)."""
    result = await NotificationService(db).send_report(current)
    return SendNowResponse(**result)
