"""MongoDB index definitions. Idempotent — safe to run on every startup.

The most important line here is the UNIQUE index on tenders
(reference_number, source_site_id): it guarantees the same tender is never stored
twice, even if two scrape runs race. The repository upserts on this key.
"""

from __future__ import annotations

from pymongo import ASCENDING, DESCENDING
from pymongo.asynchronous.database import AsyncDatabase

from app.core.logging import logger


async def ensure_indexes(db: AsyncDatabase) -> None:
    """Create every index the application relies on. Idempotent."""

    # users: unique email
    await db["users"].create_index([("email", ASCENDING)], unique=True, name="uniq_email")

    # site_configs: fetch a user's sites, and active-only worklists
    await db["site_configs"].create_index(
        [("created_by_user_id", ASCENDING), ("is_active", ASCENDING)],
        name="user_active",
    )

    # tenders: THE dedup guarantee + query-support indexes
    await db["tenders"].create_index(
        [("reference_number", ASCENDING), ("source_site_id", ASCENDING)],
        unique=True,
        name="uniq_reference_per_site",
    )
    await db["tenders"].create_index([("keywords_matched", ASCENDING)], name="keywords_matched")
    await db["tenders"].create_index([("created_at", DESCENDING)], name="created_at_desc")

    # notification_schedules: one schedule per user
    await db["notification_schedules"].create_index(
        [("user_id", ASCENDING)], unique=True, name="uniq_user"
    )

    # in_app_notifications: "my unseen notifications, newest first"
    await db["in_app_notifications"].create_index(
        [("user_id", ASCENDING), ("seen", ASCENDING), ("created_at", DESCENDING)],
        name="user_seen_created",
    )

    # domain_rate_limit_state: one state doc per domain
    await db["domain_rate_limit_state"].create_index(
        [("domain", ASCENDING)], unique=True, name="uniq_domain"
    )

    # scraper_runs: recent runs per site
    await db["scraper_runs"].create_index(
        [("site_id", ASCENDING), ("start_time", DESCENDING)], name="site_start"
    )

    logger.info("MongoDB indexes ensured.")
