"""Phase 1 — SiteConfig CRUD & lossless round-trip of nested models."""

from __future__ import annotations

from bson import ObjectId

from app.models.enums import ContentType
from app.models.site_config import ExtractionRules, RateLimitConfig, SiteConfig
from app.repositories.site_config_repo import SiteConfigRepo


async def test_nested_models_roundtrip(db) -> None:  # noqa: ANN001
    """Nested ExtractionRules / RateLimitConfig survive a save+load unchanged."""
    repo = SiteConfigRepo(db)
    user_id = ObjectId()

    site = SiteConfig(
        name="Sidwaya",
        base_url="https://www.sidwaya.info/appels-offres/",
        content_type=ContentType.HTML,
        extraction_rules=ExtractionRules(list_selector="article.tender", title_selector="h2"),
        rate_limit_config=RateLimitConfig(min_delay_ms=2000, max_delay_ms=6000, daily_cap=150),
        created_by_user_id=user_id,
    )
    saved = await repo.insert(site)

    loaded = await repo.find_by_id(saved.id)
    assert loaded is not None
    assert loaded.extraction_rules.list_selector == "article.tender"
    assert loaded.rate_limit_config.daily_cap == 150
    assert loaded.created_by_user_id == user_id           # ObjectId preserved
    assert loaded.base_url == "https://www.sidwaya.info/appels-offres"  # slash normalized


async def test_crud_and_find_by_user(db) -> None:  # noqa: ANN001
    repo = SiteConfigRepo(db)
    user_id = ObjectId()

    a = await repo.insert(
        SiteConfig(
            name="A",
            base_url="https://a.bf",
            content_type=ContentType.PDF,
            created_by_user_id=user_id,
        )
    )
    await repo.insert(
        SiteConfig(
            name="B",
            base_url="https://b.bf",
            content_type=ContentType.PDF,
            created_by_user_id=ObjectId(),  # different owner
        )
    )

    mine = await repo.find_by_user(user_id)
    assert len(mine) == 1
    assert mine[0].name == "A"

    # update (toggle inactive) then delete
    updated = await repo.update_by_id(a.id, {"is_active": False})
    assert updated is not None and updated.is_active is False
    assert await repo.delete_by_id(a.id) is True
    assert await repo.find_by_id(a.id) is None
