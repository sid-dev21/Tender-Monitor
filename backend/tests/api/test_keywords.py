"""Phase 8 - keyword filtering + user keyword management (real app + Mongo)."""

from __future__ import annotations

import httpx
from bson import ObjectId

from app.models.enums import ContentType, TenderStatus
from app.models.tender import Tender
from app.repositories.tender_repo import TenderRepo
from app.services.keyword_matcher import matched_keywords
from app.services.keyword_normalizer import normalize, normalize_list


def _tender(title: str, ref: str) -> Tender:
    return Tender(
        title=title,
        reference_number=ref,
        source_site_id=ObjectId(),
        extraction_type=ContentType.HTML,
        status=TenderStatus.PARSED,
        raw_text=title,
    )


async def _auth(client: httpx.AsyncClient) -> dict[str, str]:
    creds = {"email": "kw@example.com", "password": "Passw0rd123"}
    await client.post("/api/auth/register", json=creds)
    tokens = (await client.post("/api/auth/login", json=creds)).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_normalize_strips_accents_and_case() -> None:
    assert normalize("École") == "ecole"
    assert normalize("  ROUTE   Nationale ") == "route nationale"
    assert normalize_list(["Route", "route", "ÉCOLE"]) == ["route", "ecole"]


def test_matcher_is_accent_insensitive() -> None:
    t = _tender("Construction d'une école primaire", "R-1")
    assert matched_keywords(t, ["ecole"]) == ["ecole"]  # keyword has no accent, title does


async def test_query_filters_by_keyword(client: httpx.AsyncClient, db) -> None:  # noqa: ANN001
    repo = TenderRepo(db)
    await repo.insert(_tender("Rehabilitation de route nationale", "R-1"))
    await repo.insert(_tender("Construction d'une ecole", "R-2"))
    await repo.insert(_tender("Fourniture de materiel informatique", "R-3"))
    h = await _auth(client)

    r = await client.get("/api/tenders", params={"keywords": "route"}, headers=h)
    assert r.status_code == 200
    titles = [t["title"] for t in r.json()]
    assert titles == ["Rehabilitation de route nationale"]
    assert r.json()[0]["matched_keywords"] == ["route"]


async def test_mine_uses_saved_keywords(client: httpx.AsyncClient, db) -> None:  # noqa: ANN001
    repo = TenderRepo(db)
    await repo.insert(_tender("Route nationale RN1", "R-1"))
    await repo.insert(_tender("Ecole primaire", "R-2"))
    h = await _auth(client)

    # set keywords (with accent + mixed case -> normalized server-side)
    r = await client.patch("/api/users/me/keywords", json={"keywords": ["Route", "école"]}, headers=h)
    assert r.json()["keywords"] == ["route", "ecole"]

    r = await client.get("/api/tenders/mine", headers=h)
    refs = {t["reference_number"] for t in r.json()}
    assert refs == {"R-1", "R-2"}  # both match one of the saved keywords
