"""Request/response schemas for notifications and schedule."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import NotificationFrequency
from app.models.notification import InAppNotification
from app.models.schedule import NotificationSchedule, TIME_OF_DAY_PATTERN


class NotificationEmailsUpdate(BaseModel):
    emails: list[EmailStr] = Field(default_factory=list, max_length=5)


class InAppNotificationResponse(BaseModel):
    id: str
    tender_ids: list[str]
    seen: bool
    created_at: datetime

    @classmethod
    def from_notification(cls, n: InAppNotification) -> "InAppNotificationResponse":
        return cls(
            id=str(n.id),
            tender_ids=[str(t) for t in n.tender_ids],
            seen=n.seen,
            created_at=n.created_at,
        )


class SendNowResponse(BaseModel):
    sent: bool
    count: int
    emailed: bool


class ScheduleRequest(BaseModel):
    frequency: NotificationFrequency = NotificationFrequency.DAILY
    time: str = Field(default="08:00", pattern=TIME_OF_DAY_PATTERN)
    timezone: str = "Africa/Ouagadougou"
    is_active: bool = True


class ScheduleResponse(BaseModel):
    frequency: NotificationFrequency
    time: str
    timezone: str
    is_active: bool
    last_sent_at: datetime | None

    @classmethod
    def from_schedule(cls, s: NotificationSchedule) -> "ScheduleResponse":
        return cls(
            frequency=s.frequency,
            time=s.time,
            timezone=s.timezone,
            is_active=s.is_active,
            last_sent_at=s.last_sent_at,
        )
