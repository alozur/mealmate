import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_me_with_authelia_headers(client: AsyncClient):
    headers = {
        "Remote-User": "testuser",
        "Remote-Email": "test@example.com",
        "Remote-Name": "Test User",
        "Remote-Groups": "users",
    }
    response = await client.get("/api/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_me_without_headers_returns_401(client: AsyncClient):
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_auto_provisions_new_user(client: AsyncClient):
    headers = {
        "Remote-User": "newuser",
        "Remote-Email": "new@example.com",
        "Remote-Name": "New Person",
        "Remote-Groups": "users",
    }
    response = await client.get("/api/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == "new@example.com"

    response2 = await client.get("/api/auth/me", headers=headers)
    assert response2.json()["id"] == response.json()["id"]
