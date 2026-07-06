"""Phase 1 — Tender repository dedup behavior against a real MongoDB."""

from __future__ import annotations

import pytest
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.models.enums import ContentType, TenderStatus
from app.models.tender import Tender
from app.repositories.tender_repo import TenderRepo


def _tender(ref: str, site_id: ObjectId, *, title: str = "Route Ouaga-Bobo") -> Tender:
    return Tender(
        title=title,
        reference_number=ref,
        source_site_id=site_id,
        extraction_type=ContentType.PDF,
        status=TenderStatus.PARSED,
    )


async def test_upsert_creates_then_dedupes(db) -> None:  # noqa: ANN001
    """Same (reference, site) upserted twice => one doc, times_seen bumped."""
    repo = TenderRepo(db)
    site = ObjectId()

    first, created1 = await repo.upsert_by_reference(_tender("AON-2025-001", site))
    assert created1 is True
    assert first.times_seen == 1

    # Second scrape of the same tender — must NOT create a duplicate.
    second, created2 = await repo.upsert_by_reference(
        _tender("AON-2025-001", site, title="Route Ouaga-Bobo (updated)")
    )
    assert created2 is False
    assert second.times_seen == 2
    assert second.id == first.id                      # same document
    assert second.title == "Route Ouaga-Bobo (updated)"  # mutable field refreshed
    assert await repo.count() == 1                     # exactly one tender stored


async def test_same_reference_different_site_is_distinct(db) -> None:  # noqa: ANN001
    """The dedup key includes the site: same ref on two sites => two tenders."""
    repo = TenderRepo(db)
    site_a, site_b = ObjectId(), ObjectId()

    await repo.upsert_by_reference(_tender("AON-2025-001", site_a))
    _, created = await repo.upsert_by_reference(_tender("AON-2025-001", site_b))

    assert created is True
    assert await repo.count() == 2


async def test_unique_index_blocks_raw_duplicate(db) -> None:  # noqa: ANN001
    """The DB-level unique index rejects a duplicate that bypasses the upsert."""
    repo = TenderRepo(db)
    site = ObjectId()
    await repo.insert(_tender("AON-2025-042", site))

    with pytest.raises(DuplicateKeyError):
        await repo.insert(_tender("AON-2025-042", site))
