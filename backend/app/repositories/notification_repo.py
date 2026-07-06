"""Repository for InAppNotification documents."""

from __future__ import annotations

from typing import ClassVar

from bson import ObjectId

from app.models.notification import InAppNotification
from app.repositories.base import BaseRepository


class InAppNotificationRepo(BaseRepository[InAppNotification]):
    collection_name: ClassVar[str] = "in_app_notifications"
    model = InAppNotification

    async def find_for_user(
        self, user_id: str | ObjectId, *, unseen_only: bool = False, limit: int = 50
    ) -> list[InAppNotification]:
        flt: dict = {"user_id": self._oid(user_id)}
        if unseen_only:
            flt["seen"] = False
        return await self.find(flt, limit=limit, sort=[("created_at", -1)])

    async def mark_seen(self, notification_id: str | ObjectId) -> InAppNotification | None:
        return await self.update_by_id(notification_id, {"seen": True})
