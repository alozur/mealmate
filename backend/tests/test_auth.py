import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import hash_password
from app.models import Profile, User


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    resp = await client.post(
        "/api/auth/register",
        json={
            "email": "user1@example.com",
            "password": "securepass123",
            "invite_code": "test-invite",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "user1@example.com"
    assert "id" in body
    assert "mealmate_auth" in resp.cookies


@pytest.mark.asyncio
async def test_register_bad_invite_code(client: AsyncClient):
    resp = await client.post(
        "/api/auth/register",
        json={
            "email": "user1@example.com",
            "password": "securepass123",
            "invite_code": "wrong-code",
        },
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    data = {
        "email": "dup@example.com",
        "password": "securepass123",
        "invite_code": "test-invite",
    }
    resp1 = await client.post("/api/auth/register", json=data)
    assert resp1.status_code == 201
    resp2 = await client.post("/api/auth/register", json=data)
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_register_max_users(client: AsyncClient, db_session: AsyncSession):
    for i in range(2):
        user = User(
            email=f"existing{i}@example.com",
            hashed_password=hash_password("password123"),
        )
        db_session.add(user)
    await db_session.commit()

    resp = await client.post(
        "/api/auth/register",
        json={
            "email": "third@example.com",
            "password": "securepass123",
            "invite_code": "test-invite",
        },
    )
    assert resp.status_code == 403
    assert "closed" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_short_password(client: AsyncClient):
    resp = await client.post(
        "/api/auth/register",
        json={
            "email": "user1@example.com",
            "password": "short",
            "invite_code": "test-invite",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_invalid_email(client: AsyncClient):
    resp = await client.post(
        "/api/auth/register",
        json={
            "email": "not-an-email",
            "password": "securepass123",
            "invite_code": "test-invite",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, db_session: AsyncSession):
    user = User(
        email="login@example.com",
        hashed_password=hash_password("mypassword123"),
    )
    db_session.add(user)
    await db_session.commit()

    resp = await client.post(
        "/api/auth/login",
        json={"email": "login@example.com", "password": "mypassword123"},
    )
    assert resp.status_code == 200
    assert "mealmate_auth" in resp.cookies
    assert resp.json()["email"] == "login@example.com"


@pytest.mark.asyncio
async def test_login_case_insensitive_email(client: AsyncClient, db_session: AsyncSession):
    user = User(
        email="case@example.com",
        hashed_password=hash_password("mypassword123"),
    )
    db_session.add(user)
    await db_session.commit()

    resp = await client.post(
        "/api/auth/login",
        json={"email": "CASE@Example.com", "password": "mypassword123"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, db_session: AsyncSession):
    user = User(
        email="wrong@example.com",
        hashed_password=hash_password("correctpassword"),
    )
    db_session.add(user)
    await db_session.commit()

    resp = await client.post(
        "/api/auth/login",
        json={"email": "wrong@example.com", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    resp = await client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "password123"},
    )
    assert resp.status_code == 401


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
    assert "mealmate_auth" in resp.headers.get("set-cookie", "")


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
    other_user = User(
        email="other@example.com",
        hashed_password=hash_password("password123"),
    )
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    profile_resp = await auth_client.post(
        "/api/profiles",
        json={"name": "Maria", "goal": "fat_loss"},
    )
    profile_id = profile_resp.json()["id"]

    result = await db_session.execute(
        select(Profile).where(Profile.id == profile_id)
    )
    profile = result.scalar_one()
    profile.user_id = other_user.id
    await db_session.commit()

    resp = await auth_client.put(f"/api/auth/link-profile/{profile_id}")
    assert resp.status_code == 409
