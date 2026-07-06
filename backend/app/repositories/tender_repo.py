"""Repository for Tender documents, including the deduplication upsert."""

from __future__ import annotations

from typing import ClassVar

from app.models.base import utcnow
from app.models.tender import Tender
from app.repositories.base import BaseRepository


class TenderRepo(BaseRepository[Tender]):
    collection_name: ClassVar[str] = "tenders"
    model = Tender

    async def upsert_by_reference(self, tender: Tender) -> tuple[Tender, bool]:
        """Insert a new tender, or bump an existing one, keyed by (reference, site).

        This is the dedup core. The same reference from the same site is the SAME
        tender across scrape runs. On a re-scrape we:
          - refresh the mutable fields ($set) in case the notice changed,
          - increment times_seen ($inc),
          - NEVER touch created_at or the keyword-match fields (managed elsewhere).

        A unique index on (reference_number, source_site_id) makes this safe even
        under concurrent runs. Returns (tender, created) where created is True iff a
        new document was inserted.
        """
        key = {
            "reference_number": tender.reference_number,
            "source_site_id": tender.source_site_id,
        }

        data = self._to_doc(tender)
        # Fields that must not be overwritten by a plain re-scrape:
        data.pop("_id", None)
        created_at = data.pop("created_at")
        data.pop("times_seen", None)          # handled by $inc
        data.pop("keywords_matched", None)    # managed by the keyword matcher (Phase 8)
        data.pop("matched_users", None)       # managed by the keyword matcher (Phase 8)
        for k in key:                          # keys live in $setOnInsert, not $set
            data.pop(k, None)
        data["updated_at"] = utcnow()

        update = {
            "$set": data,
            "$setOnInsert": {**key, "created_at": created_at},
            "$inc": {"times_seen": 1},
        }

        result = await self.collection.update_one(key, update, upsert=True)
        created = result.upserted_id is not None
        stored = await self.collection.find_one(key)
        return self.model.model_validate(stored), created

    async def find_by_keywords(
        self, keywords: list[str], *, limit: int = 50, skip: int = 0
    ) -> list[Tender]:
        """Tenders whose precomputed keywords_matched intersects the given list."""
        flt = {"keywords_matched": {"$in": keywords}} if keywords else {}
        return await self.find(flt, limit=limit, skip=skip, sort=[("created_at", -1)])
