"""Remove ONLY the seeded demo tenders (those from scripts/seed_demo.py).

Real scraped tenders are untouched — this deletes only documents whose
source_site_id is the demo sentinel. Run:  uv run python -m scripts.clear_demo
"""

from __future__ import annotations

import asyncio

from app.core import db as db_module
from app.core.logging import configure_logging, logger
from scripts.seed_demo import DEMO_SITE_ID


async def _main() -> None:
    configure_logging()
    await db_module.connect()
    try:
        result = await db_module.get_db()["tenders"].delete_many(
            {"source_site_id": DEMO_SITE_ID}
        )
        logger.info("Removed {} demo tenders.", result.deleted_count)
    finally:
        await db_module.disconnect()


if __name__ == "__main__":
    asyncio.run(_main())
