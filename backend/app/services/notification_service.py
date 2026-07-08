"""Notification pipeline: find matching tenders, store in-app, email, update state."""

from __future__ import annotations

from pymongo.asynchronous.database import AsyncDatabase

from app.models.base import utcnow
from app.models.notification import InAppNotification
from app.models.tender import Tender
from app.models.user import User
from app.repositories.notification_repo import InAppNotificationRepo
from app.repositories.schedule_repo import ScheduleRepo
from app.repositories.tender_repo import TenderRepo
from app.services.keyword_matcher import filter_tenders
from app.services.notifiers.email import send_tender_report


class NotificationService:
    def __init__(self, db: AsyncDatabase) -> None:
        self._tenders = TenderRepo(db)
        self._schedules = ScheduleRepo(db)
        self._inapp = InAppNotificationRepo(db)

    async def build_matching(self, user: User) -> list[Tender]:
        """Tenders matching the user's keywords, created since their last report."""
        if not user.keywords:
            return []  # no keywords => no alerts (never notify about everything)
        schedule = await self._schedules.find_by_user(user.id)
        flt: dict = {}
        if schedule is not None and schedule.last_sent_at is not None:
            flt["created_at"] = {"$gt": schedule.last_sent_at}
        tenders = await self._tenders.find(flt, limit=500, sort=[("created_at", -1)])
        return filter_tenders(tenders, user.keywords)

    async def send_report(self, user: User) -> dict:
        """Build + deliver a report (in-app always, email if recipients set)."""
        tenders = await self.build_matching(user)
        if not tenders:
            return {"sent": False, "count": 0, "emailed": False}

        if user.in_app_notifications_enabled:
            await self._inapp.insert(
                InAppNotification(user_id=user.id, tender_ids=[t.id for t in tenders if t.id])
            )

        emailed = False
        if user.notification_emails:
            await send_tender_report(user.notification_emails, tenders)
            emailed = True

        # Advance the watermark so the next report only includes newer tenders.
        schedule = await self._schedules.find_by_user(user.id)
        if schedule is not None:
            await self._schedules.update_by_id(schedule.id, {"last_sent_at": utcnow()})

        return {"sent": True, "count": len(tenders), "emailed": emailed}
