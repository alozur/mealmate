import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Profile, User


@pytest.mark.asyncio
async def test_register_returns_410(client: AsyncClient):
    resp = await client.post(
        "/api/auth/register",
        json={
            "email": "user1@example.com",
            "password": "securepass123",
            "invite_code": "test-invite",
        },
    )
    assert resp.status_code == 410


@pytest.mark.asyncio
async def test_login_returns_410(client: AsyncClient):
    resp = await client.post(
        "/api/auth/login",
        json={"email": "login@example.com", "password": "mypassword123"},
    )
    assert resp.status_code == 410


@pytest.mark.asyncio
async def test_me_authenticated(auth_client: AsyncClient):
    resp = await auth_client.get("/api/auth/me")
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "test@example.com"
    assert "id" in body


@pytest.mark.asyncio
async def test_me_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_logout(auth_client: AsyncClient):
    resp = await auth_client.post("/api/auth/logout")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_link_profile(auth_client: AsyncClient, test_user):
    profile_resp = await auth_client.post(
        "/api/profiles",
        json={"name": "Alonso", "goal": "muscle_gain"},
    )
    profile_id = profile_resp.json()["id"]

    resp = await auth_client.put(f"/api/auth/link-profile/{profile_id}")
    assert resp.status_code == 200
    assert resp.json()["user_id"] == test_user.id


@pytest.mark.asyncio
async def test_protected_route_without_auth(client: AsyncClient):
    resp = await client.get("/api/profiles")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_link_profile_already_taken(
    auth_client: AsyncClient, db_session: AsyncSession
):
    other_user = User(email="other@example.com")
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    profile_resp = await auth_client.post(
        "/api/profiles",
        json={"name": "Maria", "goal": "fat_loss"},
    )
    profile_id = profile_resp.json()["id"]

    from sqlalchemy import select

    result = await db_session.execute(select(Profile).where(Profile.id == profile_id))
    profile = result.scalar_one()
    profile.user_id = other_user.id
    await db_session.commit()

    resp = await auth_client.put(f"/api/auth/link-profile/{profile_id}")
    assert resp.status_code == 409
