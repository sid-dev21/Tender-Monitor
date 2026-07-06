"""Repository for NotificationSchedule documents."""

from __future__ import annotations

from typing import ClassVar

from bson import ObjectId

from app.models.schedule import NotificationSchedule
from app.repositories.base import BaseRepository


class ScheduleRepo(BaseRepository[NotificationSchedule]):
    collection_name: ClassVar[str] = "notification_schedules"
    model = NotificationSchedule

    async def find_by_user(self, user_id: str | ObjectId) -> NotificationSchedule | None:
        return await self.find_one({"user_id": self._oid(user_id)})

    async def find_all_active(self) -> list[NotificationSchedule]:
        """All active schedules — used to rebuild cron jobs on startup."""
        return await self.find({"is_active": True})
