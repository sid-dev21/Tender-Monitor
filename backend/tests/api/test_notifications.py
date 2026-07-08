"""Phase 9 - notifications: MailHog email, in-app, max-5, schedule (real infra)."""

from __future__ import annotations

import httpx
import pytest
from bson import ObjectId

from app.models.enums import ContentType, TenderStatus
from app.models.tender import Tender
from app.repositories.tender_repo import TenderRepo

CREDS = {"email": "notify@example.com", "password": "Passw0rd123"}


def _tender(title: str, ref: str) -> Tender:
    return Tender(
        title=title,
        reference_number=ref,
        source_site_id=ObjectId(),
        extraction_type=ContentType.HTML,
        status=TenderStatus.PARSED,
        raw_text=title,
        estimated_budget=75_000_000,
    )


async def _auth(client: httpx.AsyncClient) -> dict[str, str]:
    await client.post("/api/auth/register", json=CREDS)
    tokens = (await client.post("/api/auth/login", json=CREDS)).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def test_max_5_notification_emails(client: httpx.AsyncClient) -> None:
    h = await _auth(client)
    six = [f"r{i}@example.com" for i in range(6)]
    r = await client.patch("/api/users/me/notification-emails", json={"emails": six}, headers=h)
    assert r.status_code == 422  # schema cap rejects 6


async def test_in_app_notification_flow(client: httpx.AsyncClient, db) -> None:  # noqa: ANN001
    h = await _auth(client)
    await client.patch("/api/users/me/keywords", json={"keywords": ["route"]}, headers=h)
    await TenderRepo(db).insert(_tender("Rehabilitation de route nationale", "R-1"))

    sent = await client.post("/api/notifications/send-now", headers=h)
    assert sent.json() == {"sent": True, "count": 1, "emailed": False}

    listed = (await client.get("/api/notifications", headers=h)).json()
    assert len(listed) == 1 and listed[0]["seen"] is False

    notif_id = listed[0]["id"]
    seen = await client.patch(f"/api/notifications/{notif_id}/mark-seen", headers=h)
    assert seen.json()["seen"] is True


async def test_schedule_create_and_update(client: httpx.AsyncClient) -> None:
    h = await _auth(client)
    r = await client.post(
        "/api/notification-schedule",
        json={"frequency": "daily", "time": "08:30", "timezone": "Africa/Ouagadougou"},
        headers=h,
    )
    assert r.status_code == 200 and r.json()["time"] == "08:30"

    r = await client.post(
        "/api/notification-schedule",
        json={"frequency": "weekly", "time": "07:00", "timezone": "Europe/Berlin"},
        headers=h,
    )
    assert r.json()["frequency"] == "weekly" and r.json()["timezone"] == "Europe/Berlin"


@pytest.mark.slow
async def test_email_delivered_to_mailhog(
    client: httpx.AsyncClient, db, mailhog: str
) -> None:  # noqa: ANN001
    h = await _auth(client)
    await client.patch(
        "/api/users/me/notification-emails",
        json={"emails": ["client1@example.com", "client2@example.com"]},
        headers=h,
    )
    await client.patch("/api/users/me/keywords", json={"keywords": ["route"]}, headers=h)
    await TenderRepo(db).insert(_tender("Rehabilitation de route nationale", "R-1"))

    result = await client.post("/api/notifications/send-now", headers=h)
    assert result.json() == {"sent": True, "count": 1, "emailed": True}

    # The real SMTP message was caught by MailHog.
    messages = httpx.get(f"{mailhog}/api/v2/messages", timeout=5).json()
    assert messages["total"] >= 1
    latest = messages["items"][0]

    recipients = latest["Raw"]["To"]  # list of envelope recipients
    assert "client1@example.com" in recipients
    assert "client2@example.com" in recipients

    subject = latest["Content"]["Headers"]["Subject"][0]
    assert "Tender Monitor" in subject
