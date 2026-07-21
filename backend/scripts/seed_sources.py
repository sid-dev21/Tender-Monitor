"""Seed the curated, VERIFIED tender sources into a user's account.

Every source here was fetched and tested against the real engine:
  - the PDF sources really expose tender documents (counts verified);
  - the HTML demo portal really extracts 4 parsed tenders;
  - ARMP Guinée exposes no tender text on its landing page — it is included to
    demonstrate the sub-page discovery feature.

Idempotent: a source is skipped if the user already has one with the same URL.

Run:  uv run python -m scripts.seed_sources [user@email]
      (defaults to the first user in the database)
"""

from __future__ import annotations

import asyncio
import sys

from app.core import db as db_module
from app.core.logging import configure_logging, logger
from app.models.enums import ContentType
from app.models.site_config import ExtractionRules, SiteConfig
from app.repositories.site_config_repo import SiteConfigRepo
from app.repositories.user_repo import UserRepo

# name, url, content_type, rules, locale, timezone
CURATED: list[tuple[str, str, ContentType, ExtractionRules, str, str]] = [
    (
        "Portail de démonstration",
        "http://localhost:5173/demo-appels-offres.html",
        ContentType.HTML,
        ExtractionRules(),  # auto-detects the tender blocks
        "fr-FR",
        "Africa/Ouagadougou",
    ),
    (
        "ARCOP — Burkina Faso",
        "https://www.arcop.bf/appels-doffres/",
        ContentType.PDF,
        # ARCOP serves PDFs at /telechargement/{id} with no .pdf suffix.
        ExtractionRules(pdf_url_pattern=r"telechargement/\d+"),
        "fr-FR",
        "Africa/Ouagadougou",
    ),
    (
        "DGMP — Mali",
        "https://dgmp.gouv.ml",
        ContentType.PDF,
        ExtractionRules(),  # default a[href$=".pdf"] matches its ..._AAO_....pdf files
        "fr-FR",
        "Africa/Bamako",
    ),
    (
        "Quotidien des Marchés Publics — Burkina Faso",
        "https://finances.gov.bf",
        ContentType.PDF,
        ExtractionRules(),
        "fr-FR",
        "Africa/Ouagadougou",
    ),
    (
        "ARMP — Guinée",
        "https://armpguinee.org/appels-doffres",
        ContentType.HTML,
        ExtractionRules(),  # no tender text on the landing page -> shows discovery
        "fr-FR",
        "Africa/Conakry",
    ),
]


async def _main() -> None:
    configure_logging()
    await db_module.connect()
    try:
        db = db_module.get_db()
        users = UserRepo(db)

        email = sys.argv[1] if len(sys.argv) > 1 else None
        user = await users.find_by_email(email) if email else None
        if user is None:
            found = await users.find({}, limit=1)
            if not found:
                logger.error("No user in the database. Register in the app first.")
                return
            user = found[0]
        logger.info("Seeding sources for user {}", user.email)

        repo = SiteConfigRepo(db)
        existing = {s.base_url for s in await repo.find_by_user(user.id)}
        added = 0
        for name, url, ctype, rules, locale, tz in CURATED:
            if url.rstrip("/") in existing:
                continue
            await repo.insert(
                SiteConfig(
                    name=name,
                    base_url=url,
                    content_type=ctype,
                    extraction_rules=rules,
                    locale=locale,
                    timezone=tz,
                    created_by_user_id=user.id,
                )
            )
            added += 1
        logger.info("Sources seeded: {} added, {} already present.", added, len(existing))
    finally:
        await db_module.disconnect()


if __name__ == "__main__":
    asyncio.run(_main())
