from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from tests.conftest import SAMPLE_AI_MEALS, SAMPLE_AI_REGENERATED, make_openai_response


async def _create_profiles(client: AsyncClient) -> list[dict]:
    """Helper to create two test profiles."""
    profiles = []
    for data in [
        {
            "name": "Alonso",
            "goal": "muscle_gain",
            "calorie_target": 2800,
            "protein_target": 200,
        },
        {
            "name": "Maria",
            "goal": "fat_loss",
            "calorie_target": 1800,
            "protein_target": 130,
        },
    ]:
        resp = await client.post("/api/profiles", json=data)
        profiles.append(resp.json())
    return profiles


@pytest.mark.asyncio
async def test_generate_meal_plan(auth_client: AsyncClient):
    await _create_profiles(auth_client)

    mock_response = make_openai_response(SAMPLE_AI_MEALS)
    mock_create = AsyncMock(return_value=mock_response)

    with patch("app.openai_client.AsyncOpenAI") as MockOpenAI:
        instance = MockOpenAI.return_value
        instance.chat.completions.create = mock_create

        resp = await auth_client.post("/api/meal-plans/generate", json={})

    assert resp.status_code == 201
    body = resp.json()
    assert "id" in body
    assert body["status"] == "active"
    assert len(body["meals"]) == 2
    assert body["meals"][0]["name"] == "Grilled Chicken Salad"
    assert len(body["meals"][0]["portions"]) == 2
    assert len(body["meals"][0]["ingredients"]) == 2


@pytest.mark.asyncio
async def test_generate_meal_plan_no_profiles(auth_client: AsyncClient):
    resp = await auth_client.post("/api/meal-plans/generate", json={})
    assert resp.status_code == 400
    assert "No profiles" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_list_meal_plans(auth_client: AsyncClient):
    await _create_profiles(auth_client)

    mock_response = make_openai_response(SAMPLE_AI_MEALS)
    mock_create = AsyncMock(return_value=mock_response)

    with patch("app.openai_client.AsyncOpenAI") as MockOpenAI:
        instance = MockOpenAI.return_value
        instance.chat.completions.create = mock_create
        await auth_client.post("/api/meal-plans/generate", json={})

    resp = await auth_client.get("/api/meal-plans")
    assert resp.status_code == 200
    plans = resp.json()
    assert len(plans) >= 1


@pytest.mark.asyncio
async def test_get_meal_plan_detail(auth_client: AsyncClient):
    await _create_profiles(auth_client)

    mock_response = make_openai_response(SAMPLE_AI_MEALS)
    mock_create = AsyncMock(return_value=mock_response)

    with patch("app.openai_client.AsyncOpenAI") as MockOpenAI:
        instance = MockOpenAI.return_value
        instance.chat.completions.create = mock_create
        create_resp = await auth_client.post("/api/meal-plans/generate", json={})

    plan_id = create_resp.json()["id"]
    resp = await auth_client.get(f"/api/meal-plans/{plan_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == plan_id
    assert len(body["meals"]) == 2


@pytest.mark.asyncio
async def test_get_meal_plan_not_found(auth_client: AsyncClient):
    resp = await auth_client.get("/api/meal-plans/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_regenerate_meal(auth_client: AsyncClient):
    await _create_profiles(auth_client)

    mock_response = make_openai_response(SAMPLE_AI_MEALS)
    mock_regen_response = make_openai_response(SAMPLE_AI_REGENERATED)
    mock_create = AsyncMock(side_effect=[mock_response, mock_regen_response])

    with patch("app.openai_client.AsyncOpenAI") as MockOpenAI:
        instance = MockOpenAI.return_value
        instance.chat.completions.create = mock_create

        create_resp = await auth_client.post("/api/meal-plans/generate", json={})
        plan_id = create_resp.json()["id"]
        meal_id = create_resp.json()["meals"][0]["id"]

        resp = await auth_client.post(
            f"/api/meal-plans/{plan_id}/regenerate-meal/{meal_id}"
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Turkey Wrap"
    assert body["meal_type"] == "lunch"
    assert body["day_of_week"] == 1


@pytest.mark.asyncio
async def test_regenerate_meal_not_found(auth_client: AsyncClient):
    await _create_profiles(auth_client)

    mock_response = make_openai_response(SAMPLE_AI_MEALS)
    mock_create = AsyncMock(return_value=mock_response)

    with patch("app.openai_client.AsyncOpenAI") as MockOpenAI:
        instance = MockOpenAI.return_value
        instance.chat.completions.create = mock_create
        create_resp = await auth_client.post("/api/meal-plans/generate", json={})

    plan_id = create_resp.json()["id"]
    resp = await auth_client.post(
        f"/api/meal-plans/{plan_id}/regenerate-meal/nonexistent"
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_meal_plan(auth_client: AsyncClient):
    await _create_profiles(auth_client)

    mock_response = make_openai_response(SAMPLE_AI_MEALS)
    mock_create = AsyncMock(return_value=mock_response)

    with patch("app.openai_client.AsyncOpenAI") as MockOpenAI:
        instance = MockOpenAI.return_value
        instance.chat.completions.create = mock_create
        create_resp = await auth_client.post("/api/meal-plans/generate", json={})

    plan_id = create_resp.json()["id"]
    resp = await auth_client.delete(f"/api/meal-plans/{plan_id}")
    assert resp.status_code == 204

    resp = await auth_client.get(f"/api/meal-plans/{plan_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_meal_plan_not_found(auth_client: AsyncClient):
    resp = await auth_client.delete("/api/meal-plans/nonexistent")
    assert resp.status_code == 404
