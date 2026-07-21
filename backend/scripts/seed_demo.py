"""Seed realistic demo tenders (FR/DE/EN) for the Thursday demo.

Inserts global tenders so any logged-in user sees them on the Dashboard / Tenders
pages, and keyword filtering + notifications work live. Idempotent (upsert by
reference). Run:  uv run python -m scripts.seed_demo
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from bson import ObjectId

from app.core import db as db_module
from app.core.logging import configure_logging, logger
from app.models.enums import ContentType, ScrapeTier, TenderStatus
from app.models.tender import Tender
from app.repositories.tender_repo import TenderRepo

# A stable fake "source" so seeded tenders share a provenance.
DEMO_SITE_ID = ObjectId("650000000000000000000001")


def _in(days: int) -> datetime:
    return datetime.now(UTC) + timedelta(days=days)


def _demo_tenders() -> list[Tender]:
    common = dict(
        source_site_id=DEMO_SITE_ID,
        extraction_type=ContentType.HTML,
        scrape_tier_used=ScrapeTier.HTTPX,
        status=TenderStatus.PARSED,
    )
    rows: list[dict] = [
        dict(
            title="Construction de 3 écoles primaires dans la région du Centre",
            reference_number="AON-2026-001/MENA",
            contracting_authority="Ministère de l'Éducation Nationale",
            deadline=_in(21),
            estimated_budget=185_000_000,
            currency="XOF",
            raw_text="Construction de 3 écoles primaires. BTP construction bâtiment scolaire.",
            document_url="https://www.arcop.bf/appels-doffres/",
        ),
        dict(
            title="Réhabilitation de la route nationale RN4 (tronçon Koupéla-Fada)",
            reference_number="AON-2026-014/MI",
            contracting_authority="Ministère des Infrastructures",
            deadline=_in(9),
            estimated_budget=2_400_000_000,
            currency="XOF",
            raw_text="Réhabilitation route nationale RN4. Travaux routiers BTP.",
            document_url="https://www.arcop.bf/appels-doffres/",
        ),
        dict(
            title="Fourniture et installation d'éclairage public solaire à Ouagadougou",
            reference_number="AON-2026-022/SONABEL",
            contracting_authority="SONABEL",
            deadline=_in(30),
            estimated_budget=460_000_000,
            currency="XOF",
            raw_text="Éclairage public solaire. Lighting éclairage électrification construction.",
            document_url="https://www.arcop.bf/appels-doffres/",
        ),
        dict(
            title="Réalisation de 12 forages positifs dans la région du Sahel",
            reference_number="AON-2026-031/MEA",
            contracting_authority="Ministère de l'Eau et de l'Assainissement",
            deadline=_in(15),
            estimated_budget=96_000_000,
            currency="XOF",
            raw_text="Réalisation de forages. Hydraulique eau BTP construction.",
            document_url="https://www.arcop.bf/appels-doffres/",
        ),
        dict(
            title="Construction d'un centre de santé et de promotion sociale (CSPS)",
            reference_number="AON-2026-040/MS",
            contracting_authority="Ministère de la Santé",
            deadline=_in(5),
            estimated_budget=138_000_000,
            currency="XOF",
            raw_text="Construction CSPS centre de santé. Bâtiment BTP construction.",
            document_url="https://www.arcop.bf/appels-doffres/",
        ),
        dict(
            title="Travaux d'électrification rurale de 8 localités",
            reference_number="AON-2026-045/SONABEL",
            contracting_authority="SONABEL",
            deadline=_in(25),
            estimated_budget=780_000_000,
            currency="XOF",
            raw_text="Électrification rurale. Réseau électrique éclairage construction BTP.",
            document_url="https://www.arcop.bf/appels-doffres/",
        ),
        # --- German client sources ---
        dict(
            title="Neubau einer Grundschule in Berlin-Pankow",
            reference_number="DE-2026-0117",
            contracting_authority="Bundesamt für Bauwesen",
            deadline=_in(18),
            estimated_budget=3_250_000,
            currency="EUR",
            raw_text="Neubau Grundschule. Bau Konstruktion Ausschreibung Beleuchtung.",
            document_url="https://www.evergabe-online.de/",
        ),
        dict(
            title="Sanierung der Straßenbeleuchtung im Stadtgebiet München",
            reference_number="DE-2026-0203",
            contracting_authority="Stadt München Vergabestelle",
            deadline=_in(12),
            estimated_budget=1_180_000,
            currency="EUR",
            raw_text="Straßenbeleuchtung Sanierung. Beleuchtung lighting Bau construction.",
            document_url="https://www.evergabe-online.de/",
        ),
        # --- English source ---
        dict(
            title="Construction of a municipal water treatment facility",
            reference_number="UK-2026-088",
            contracting_authority="City of Manchester Council",
            deadline=_in(27),
            estimated_budget=4_500_000,
            currency="GBP",
            raw_text="Construction water treatment facility. Building works construction BTP.",
            document_url="https://www.find-tender.service.gov.uk/",
        ),
        dict(
            title="Marché à bons de commande pour matériaux de construction",
            reference_number="AON-2026-052/MO",
            contracting_authority="Mairie de Ouagadougou",
            deadline=_in(3),
            estimated_budget=54_000_000,
            currency="XOF",
            raw_text="Matériaux de construction ciment fer. BTP construction bâtiment.",
            document_url="https://www.arcop.bf/appels-doffres/",
        ),
    ]
    return [Tender(**common, **row) for row in rows]  # type: ignore[arg-type]


async def _main() -> None:
    configure_logging()
    await db_module.connect()
    try:
        repo = TenderRepo(db_module.get_db())
        created = 0
        for tender in _demo_tenders():
            _, is_new = await repo.upsert_by_reference(tender)
            created += int(is_new)
        logger.info("Seed complete: {} new tenders (idempotent).", created)
    finally:
        await db_module.disconnect()


if __name__ == "__main__":
    asyncio.run(_main())
