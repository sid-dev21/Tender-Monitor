"""Shared base model for every MongoDB-backed document."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.objectid import PyObjectId


def utcnow() -> datetime:
    """Timezone-aware 'now' in UTC. Always store aware datetimes."""
    return datetime.now(UTC)


class MongoModel(BaseModel):
    """Base for all persisted documents.

    - `id` maps to MongoDB's `_id` via an alias, and defaults to None for
      not-yet-inserted documents (Mongo assigns the real _id on insert).
    - `created_at` / `updated_at` are timezone-aware UTC timestamps.
    """

    model_config = ConfigDict(
        populate_by_name=True,       # allow constructing with `id=` OR `_id=`
        arbitrary_types_allowed=True,  # ObjectId is not a pydantic-native type
        str_strip_whitespace=True,   # trim incoming string fields
    )

    id: PyObjectId | None = Field(default=None, alias="_id")
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
