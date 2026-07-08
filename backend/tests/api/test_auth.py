"""Phase 10 - auth flow against the real app + real Mongo (no mocks)."""

from __future__ import annotations

import httpx

REGISTER = {"email": "sidoine@example.com", "password": "Passw0rd123"}


async def test_register_login_me_flow(client: httpx.AsyncClient) -> None:
    # register
    r = await client.post("/api/auth/register", json=REGISTER)
    assert r.status_code == 201
    assert r.json()["email"] == REGISTER["email"]

    # login -> tokens
    r = await client.post("/api/auth/login", json=REGISTER)
    assert r.status_code == 200
    tokens = r.json()
    assert tokens["token_type"] == "bearer"

    # protected route with access token
    r = await client.get(
        "/api/users/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert r.status_code == 200
    assert r.json()["email"] == REGISTER["email"]


async def test_duplicate_email_conflicts(client: httpx.AsyncClient) -> None:
    await client.post("/api/auth/register", json=REGISTER)
    r = await client.post("/api/auth/register", json=REGISTER)
    assert r.status_code == 409


async def test_weak_password_rejected(client: httpx.AsyncClient) -> None:
    r = await client.post(
        "/api/auth/register", json={"email": "x@example.com", "password": "short"}
    )
    assert r.status_code == 422  # fails min_length / strength validation


async def test_wrong_password_unauthorized(client: httpx.AsyncClient) -> None:
    await client.post("/api/auth/register", json=REGISTER)
    r = await client.post(
        "/api/auth/login", json={"email": REGISTER["email"], "password": "WrongPass999"}
    )
    assert r.status_code == 401


async def test_protected_route_requires_token(client: httpx.AsyncClient) -> None:
    r = await client.get("/api/users/me")
    assert r.status_code in (401, 403)  # no bearer credentials


async def test_refresh_returns_new_access(client: httpx.AsyncClient) -> None:
    await client.post("/api/auth/register", json=REGISTER)
    tokens = (await client.post("/api/auth/login", json=REGISTER)).json()

    r = await client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200
    new_access = r.json()["access_token"]

    r = await client.get("/api/users/me", headers={"Authorization": f"Bearer {new_access}"})
    assert r.status_code == 200
