import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_inventory_empty(auth_client: AsyncClient):
    resp = await auth_client.get("/api/inventory")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_inventory_item(auth_client: AsyncClient):
    data = {
        "name": "Pollo",
        "quantity": "500",
        "unit": "g",
        "category": "protein",
        "storage_location": "fridge",
    }
    resp = await auth_client.post("/api/inventory", json=data)
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Pollo"
    assert body["quantity"] == "500"
    assert body["unit"] == "g"
    assert body["category"] == "protein"
    assert body["storage_location"] == "fridge"
    assert "id" in body


@pytest.mark.asyncio
async def test_create_inventory_item_defaults(auth_client: AsyncClient):
    resp = await auth_client.post("/api/inventory", json={"name": "Leche"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Leche"
    assert body["category"] == "other"
    assert body["storage_location"] == "fridge"
    assert body["quantity"] is None
    assert body["unit"] is None


@pytest.mark.asyncio
async def test_update_inventory_item(auth_client: AsyncClient):
    create_resp = await auth_client.post(
        "/api/inventory",
        json={
            "name": "Leche",
            "storage_location": "fridge",
        },
    )
    item_id = create_resp.json()["id"]

    resp = await auth_client.put(
        f"/api/inventory/{item_id}",
        json={
            "name": "Leche entera",
            "quantity": "1",
            "unit": "L",
            "storage_location": "fridge",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Leche entera"
    assert resp.json()["quantity"] == "1"
    assert resp.json()["unit"] == "L"


@pytest.mark.asyncio
async def test_update_inventory_item_not_found(auth_client: AsyncClient):
    resp = await auth_client.put("/api/inventory/nonexistent", json={"name": "X"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_inventory_item(auth_client: AsyncClient):
    create_resp = await auth_client.post("/api/inventory", json={"name": "Yogur"})
    item_id = create_resp.json()["id"]

    resp = await auth_client.delete(f"/api/inventory/{item_id}")
    assert resp.status_code == 204

    resp = await auth_client.get("/api/inventory")
    assert all(item["id"] != item_id for item in resp.json())


@pytest.mark.asyncio
async def test_delete_inventory_item_not_found(auth_client: AsyncClient):
    resp = await auth_client.delete("/api/inventory/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_inventory_item_validation(auth_client: AsyncClient):
    resp = await auth_client.post("/api/inventory", json={"name": ""})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_inventory_freezer_location(auth_client: AsyncClient):
    resp = await auth_client.post(
        "/api/inventory",
        json={
            "name": "Helado",
            "storage_location": "freezer",
            "category": "dairy",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["storage_location"] == "freezer"
    assert resp.json()["category"] == "dairy"
