import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_profiles_empty(auth_client: AsyncClient):
    resp = await auth_client.get("/api/profiles")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_profile(auth_client: AsyncClient):
    data = {
        "name": "Alonso",
        "goal": "muscle_gain",
        "restrictions": ["gluten-free"],
        "calorie_target": 2800,
        "protein_target": 200,
        "carbs_target": 300,
        "fat_target": 80,
    }
    resp = await auth_client.post("/api/profiles", json=data)
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Alonso"
    assert body["goal"] == "muscle_gain"
    assert body["restrictions"] == ["gluten-free"]
    assert body["calorie_target"] == 2800
    assert "id" in body


@pytest.mark.asyncio
async def test_get_profile(auth_client: AsyncClient):
    create_resp = await auth_client.post(
        "/api/profiles",
        json={
            "name": "Maria",
            "goal": "fat_loss",
        },
    )
    profile_id = create_resp.json()["id"]

    resp = await auth_client.get(f"/api/profiles/{profile_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Maria"
    assert resp.json()["goal"] == "fat_loss"
    assert resp.json()["restrictions"] == []


@pytest.mark.asyncio
async def test_get_profile_not_found(auth_client: AsyncClient):
    resp = await auth_client.get("/api/profiles/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_profile(auth_client: AsyncClient):
    create_resp = await auth_client.post(
        "/api/profiles",
        json={
            "name": "Test",
            "goal": "maintenance",
        },
    )
    profile_id = create_resp.json()["id"]

    resp = await auth_client.put(
        f"/api/profiles/{profile_id}",
        json={
            "name": "Updated",
            "calorie_target": 3000,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated"
    assert resp.json()["calorie_target"] == 3000
    assert resp.json()["goal"] == "maintenance"  # unchanged


@pytest.mark.asyncio
async def test_update_profile_not_found(auth_client: AsyncClient):
    resp = await auth_client.put("/api/profiles/nonexistent", json={"name": "X"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_profile(auth_client: AsyncClient):
    create_resp = await auth_client.post(
        "/api/profiles",
        json={
            "name": "ToDelete",
            "goal": "fat_loss",
        },
    )
    profile_id = create_resp.json()["id"]

    resp = await auth_client.delete(f"/api/profiles/{profile_id}")
    assert resp.status_code == 204

    resp = await auth_client.get(f"/api/profiles/{profile_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_profile_not_found(auth_client: AsyncClient):
    resp = await auth_client.delete("/api/profiles/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_profile_validation(auth_client: AsyncClient):
    resp = await auth_client.post(
        "/api/profiles",
        json={
            "name": "",
            "goal": "fat_loss",
        },
    )
    assert resp.status_code == 422

    resp = await auth_client.post(
        "/api/profiles",
        json={
            "name": "Test",
            "goal": "fat_loss",
            "calorie_target": 100,  # below 500 min
        },
    )
    assert resp.status_code == 422
