"""Notification schedule API: configure when reports are sent (frequency/time/tz)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.asynchronous.database import AsyncDatabase

from app.dependencies.deps import get_current_user, get_db
from app.models.schedule import NotificationSchedule
from app.models.user import User
from app.repositories.schedule_repo import ScheduleRepo
from app.schemas.notification_dto import ScheduleRequest, ScheduleResponse

router = APIRouter(prefix="/api/notification-schedule", tags=["notifications"])


@router.get("", response_model=ScheduleResponse)
async def get_schedule(
    current: User = Depends(get_current_user),
    db: AsyncDatabase = Depends(get_db),
) -> ScheduleResponse:
    schedule = await ScheduleRepo(db).find_by_user(current.id)
    if schedule is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No schedule configured")
    return ScheduleResponse.from_schedule(schedule)


@router.post("", response_model=ScheduleResponse)
async def set_schedule(
    body: ScheduleRequest,
    current: User = Depends(get_current_user),
    db: AsyncDatabase = Depends(get_db),
) -> ScheduleResponse:
    """Create or update the user's schedule (one per user)."""
    repo = ScheduleRepo(db)
    changes = {
        "frequency": body.frequency,
        "time": body.time,
        "timezone": body.timezone,
        "is_active": body.is_active,
    }
    existing = await repo.find_by_user(current.id)
    if existing is not None:
        updated = await repo.update_by_id(existing.id, changes)
        assert updated is not None
        return ScheduleResponse.from_schedule(updated)

    schedule = NotificationSchedule(
        user_id=current.id, job_id=str(current.id), **changes
    )
    saved = await repo.insert(schedule)
    return ScheduleResponse.from_schedule(saved)
