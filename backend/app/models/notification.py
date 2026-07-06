"""InAppNotification — an in-app report item shown to the user in the frontend."""

from __future__ import annotations

from pydantic import Field

from app.models.base import MongoModel
from app.models.objectid import PyObjectId


class InAppNotification(MongoModel):
    """One notification event for a user, referencing the tenders it bundled.

    Stored in `in_app_notifications`. The frontend lists these (newest first) and
    marks them seen. `created_at` (from MongoModel) is the event time; an index on
    (user_id, seen, created_at) makes "my unseen notifications" a fast query.
    """

    user_id: PyObjectId
    tender_ids: list[PyObjectId] = Field(default_factory=list)
    seen: bool = False
