"""CLI to create all MongoDB indexes against the configured database.

Run standalone:  uv run python -m scripts.init_indexes

The index definitions live in app.core.indexes (so the app can reuse them on
startup); this script is just a runnable wrapper around them.
"""

from __future__ import annotations

import asyncio

from app.core import db as db_module
from app.core.indexes import ensure_indexes
from app.core.logging import configure_logging


async def _main() -> None:
    configure_logging()
    await db_module.connect()
    try:
        await ensure_indexes(db_module.get_db())
    finally:
        await db_module.disconnect()


if __name__ == "__main__":
    asyncio.run(_main())
