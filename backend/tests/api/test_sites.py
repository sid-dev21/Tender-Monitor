"""Phase 7 - Sites API: CRUD, ownership, auto-detect, dry-run (real app + Mongo)."""

from __future__ import annotations

import httpx

from app.repositories.tender_repo import TenderRepo
from tests.conftest import LocalServer

HTML_PAGE = """
<html><body><div class="tenders">
  <article class="tender"><h2>Ecole a Ouagadougou</h2>
    <p>AVIS D'APPEL D'OFFRES N 2025-101/MENA</p>
    <p>Date limite : 20 avril 2026</p><p>Montant : 75 000 000 FCFA</p></article>
  <article class="tender"><h2>Route nationale</h2>
    <p>AVIS D'APPEL D'OFFRES N 2025-102/MI</p>
    <p>Date limite : 5 mai 2026</p><p>Montant : 500 000 000 FCFA</p></article>
</div></body></html>
"""


async def _auth(client: httpx.AsyncClient, email: str = "a@example.com") -> dict[str, str]:
    creds = {"email": email, "password": "Passw0rd123"}
    await client.post("/api/auth/register", json=creds)
    tokens = (await client.post("/api/auth/login", json=creds)).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def test_site_crud(client: httpx.AsyncClient) -> None:
    h = await _auth(client)
    r = await client.post(
        "/api/sites",
        json={
            "name": "Sidwaya",
            "base_url": "https://www.sidwaya.info",
            "content_type": "html",
            "extraction_rules": {"list_selector": "article"},
        },
        headers=h,
    )
    assert r.status_code == 201
    site_id = r.json()["id"]

    assert len((await client.get("/api/sites", headers=h)).json()) == 1
    assert (await client.get(f"/api/sites/{site_id}", headers=h)).status_code == 200

    r = await client.patch(f"/api/sites/{site_id}", json={"is_active": False}, headers=h)
    assert r.json()["is_active"] is False

    assert (await client.delete(f"/api/sites/{site_id}", headers=h)).status_code == 204
    assert (await client.get(f"/api/sites/{site_id}", headers=h)).status_code == 404


async def test_ownership_isolation(client: httpx.AsyncClient) -> None:
    ha = await _auth(client, "owner@example.com")
    hb = await _auth(client, "other@example.com")
    r = await client.post(
        "/api/sites",
        json={"name": "A", "base_url": "https://a.bf", "content_type": "pdf"},
        headers=ha,
    )
    site_id = r.json()["id"]

    # Another user cannot see it, and their own list is empty.
    assert (await client.get(f"/api/sites/{site_id}", headers=hb)).status_code == 404
    assert (await client.get("/api/sites", headers=hb)).json() == []


async def test_create_autodetects_html(client: httpx.AsyncClient, http_server: LocalServer) -> None:
    h = await _auth(client)
    url = http_server.add("/page", "<html><body><p>" + "x" * 600 + "</p></body></html>")
    r = await client.post("/api/sites", json={"name": "Auto", "base_url": url}, headers=h)
    assert r.status_code == 201
    assert r.json()["content_type"] == "html"


async def test_dry_run_previews_without_saving(
    client: httpx.AsyncClient, http_server: LocalServer, db
) -> None:  # noqa: ANN001
    h = await _auth(client)
    url = http_server.add("/tenders", HTML_PAGE)
    r = await client.post(
        "/api/sites",
        json={
            "name": "Test",
            "base_url": url,
            "content_type": "html",
            "extraction_rules": {"list_selector": "article.tender", "title_selector": "h2"},
        },
        headers=h,
    )
    site_id = r.json()["id"]

    r = await client.post(f"/api/sites/{site_id}/test", headers=h)
    assert r.status_code == 200
    assert r.json()["count"] == 2                 # tenders previewed
    assert await TenderRepo(db).count() == 0       # but NOTHING persisted
