"""NotificationSchedule — per-user cron settings for tender reports."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator

from app.models.base import MongoModel
from app.models.enums import NotificationFrequency
from app.models.objectid import PyObjectId

# "HH:MM" in 24h form, e.g. "08:00", "23:30".
TIME_OF_DAY_PATTERN = r"^([01]\d|2[0-3]):[0-5]\d$"


class NotificationSchedule(MongoModel):
    """When to send a user's report. One document per user (unique user_id index).

    `time` + `timezone` + `frequency` are translated into an APScheduler cron job in
    Phase 9; `job_id` stores that job's id (= str(user_id)) so we can reschedule or
    remove it. `last_sent_at` bounds the "new tenders since" query in the builder.
    """

    user_id: PyObjectId
    frequency: NotificationFrequency = NotificationFrequency.DAILY
    time: str = Field(default="08:00", pattern=TIME_OF_DAY_PATTERN)
    timezone: str = "Africa/Ouagadougou"
    is_active: bool = True
    last_sent_at: datetime | None = None
    job_id: str | None = None

    @field_validator("timezone")
    @classmethod
    def _validate_timezone(cls, value: str) -> str:
        """Reject anything that is not a real IANA timezone name."""
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"Unknown timezone: {value!r}") from exc
        return value

    @property
    def hour_minute(self) -> tuple[int, int]:
        """Parse `time` into (hour, minute) for building a cron trigger."""
        hh, mm = self.time.split(":")
        return int(hh), int(mm)
