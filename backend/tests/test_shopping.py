from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from tests.conftest import SAMPLE_AI_MEALS, make_openai_response


async def _setup_plan(client: AsyncClient) -> str:
    """Create profiles and generate a plan, return plan_id."""
    for data in [
        {"name": "Alonso", "goal": "muscle_gain"},
        {"name": "Maria", "goal": "fat_loss"},
    ]:
        await client.post("/api/profiles", json=data)

    mock_response = make_openai_response(SAMPLE_AI_MEALS)
    mock_create = AsyncMock(return_value=mock_response)

    with patch("app.openai_client.AsyncOpenAI") as MockOpenAI:
        instance = MockOpenAI.return_value
        instance.chat.completions.create = mock_create
        resp = await client.post("/api/meal-plans/generate", json={})

    return resp.json()["id"]


@pytest.mark.asyncio
async def test_shopping_list(client: AsyncClient):
    plan_id = await _setup_plan(client)

    resp = await client.get(f"/api/meal-plans/{plan_id}/shopping-list")
    assert resp.status_code == 200
    body = resp.json()
    assert "categories" in body

    # Should have protein and produce categories from sample data
    assert "protein" in body["categories"]
    assert "produce" in body["categories"]

    # Check that items exist
    protein_items = body["categories"]["protein"]
    assert len(protein_items) >= 1
    names = [item["name"].lower() for item in protein_items]
    assert any("chicken" in n for n in names)


@pytest.mark.asyncio
async def test_shopping_list_not_found(client: AsyncClient):
    resp = await client.get("/api/meal-plans/nonexistent/shopping-list")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_shopping_list_aggregates_quantities(client: AsyncClient):
    plan_id = await _setup_plan(client)

    resp = await client.get(f"/api/meal-plans/{plan_id}/shopping-list")
    body = resp.json()

    # All items should have total_quantity set
    for category, items in body["categories"].items():
        for item in items:
            assert "total_quantity" in item
            assert item["total_quantity"] != ""
