import json
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Ingredient, Meal, MealPlan, MealPortion, Profile, User
from app.openai_client import generate_weekly_plan, regenerate_single_meal
from app.schemas import (
    MealPlanDetailResponse,
    MealPlanGenerate,
    MealPlanResponse,
    MealResponse,
    ProfileResponse,
)

router = APIRouter(prefix="/api/meal-plans", tags=["meal-plans"])


def _next_monday() -> date:
    today = date.today()
    days_ahead = 0 - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return today + timedelta(days=days_ahead)


async def _get_all_profiles(db: AsyncSession) -> list[ProfileResponse]:
    result = await db.execute(select(Profile).order_by(Profile.created_at))
    profiles = result.scalars().all()
    return [ProfileResponse.model_validate(p) for p in profiles]


def _map_profile_name_to_id(profiles: list[ProfileResponse]) -> dict[str, str]:
    return {p.name.lower(): p.id for p in profiles}


async def _persist_meals(
    db: AsyncSession,
    meal_plan: MealPlan,
    meals_data: list[dict],
    name_to_id: dict[str, str],
) -> None:
    for meal_data in meals_data:
        meal = Meal(
            meal_plan_id=meal_plan.id,
            day_of_week=meal_data["day_of_week"],
            meal_type=meal_data["meal_type"],
            name=meal_data["name"],
            description=meal_data.get("description"),
            recipe_steps=json.dumps(meal_data.get("recipe_steps", [])),
            prep_time_min=meal_data.get("prep_time_min"),
            cook_time_min=meal_data.get("cook_time_min"),
        )
        db.add(meal)
        await db.flush()

        for portion_data in meal_data.get("portions", []):
            profile_name = portion_data.get("profile_name", "").lower()
            profile_id = name_to_id.get(profile_name)
            if not profile_id:
                for name, pid in name_to_id.items():
                    if name in profile_name or profile_name in name:
                        profile_id = pid
                        break
            if not profile_id:
                continue

            portion = MealPortion(
                meal_id=meal.id,
                profile_id=profile_id,
                serving_size=str(portion_data.get("serving_size", "1 portion")),
                calories=int(portion_data.get("calories", 0)),
                protein_g=float(portion_data.get("protein_g", 0)),
                carbs_g=float(portion_data.get("carbs_g", 0)),
                fat_g=float(portion_data.get("fat_g", 0)),
            )
            db.add(portion)

        for ing_data in meal_data.get("ingredients", []):
            ingredient = Ingredient(
                meal_id=meal.id,
                name=ing_data["name"],
                quantity=str(ing_data.get("quantity", "")),
                unit=ing_data.get("unit"),
                category=ing_data.get("category", "pantry"),
            )
            db.add(ingredient)


@router.post("/generate", response_model=MealPlanDetailResponse, status_code=201)
async def generate_meal_plan(
    body: MealPlanGenerate,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profiles = await _get_all_profiles(db)
    if not profiles:
        raise HTTPException(
            status_code=400,
            detail="No profiles found. Create at least one profile first.",
        )

    week_start = body.week_start or _next_monday()
    week_end = week_start + timedelta(days=5)

    ai_response = await generate_weekly_plan(profiles, week_start)
    meals_data = ai_response.get("meals", [])
    if not meals_data:
        raise HTTPException(status_code=502, detail="AI did not return any meals")

    meal_plan = MealPlan(
        week_start=week_start,
        week_end=week_end,
        status="active",
    )
    db.add(meal_plan)
    await db.flush()

    name_to_id = _map_profile_name_to_id(profiles)
    await _persist_meals(db, meal_plan, meals_data, name_to_id)
    await db.commit()

    return await _get_plan_detail(db, meal_plan.id)


@router.get("", response_model=list[MealPlanResponse])
async def list_meal_plans(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(MealPlan).order_by(MealPlan.created_at.desc()))
    return result.scalars().all()


@router.get("/{plan_id}", response_model=MealPlanDetailResponse)
async def get_meal_plan(
    plan_id: str,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    plan = await _get_plan_detail(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Meal plan not found")
    return plan


@router.post("/{plan_id}/regenerate-meal/{meal_id}", response_model=MealResponse)
async def regenerate_meal(
    plan_id: str,
    meal_id: str,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    plan = await _get_plan_detail(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Meal plan not found")

    target_meal = None
    for m in plan.meals:
        if m.id == meal_id:
            target_meal = m
            break

    if not target_meal:
        raise HTTPException(status_code=404, detail="Meal not found in this plan")

    existing_meals = [m.name for m in plan.meals if m.id != meal_id]
    profiles = await _get_all_profiles(db)

    ai_response = await regenerate_single_meal(
        profiles=profiles,
        existing_meals=existing_meals,
        day_of_week=target_meal.day_of_week,
        meal_type=target_meal.meal_type,
        old_meal_name=target_meal.name,
    )

    new_meals_data = ai_response.get("meals", [])
    if not new_meals_data:
        raise HTTPException(
            status_code=502, detail="AI did not return a replacement meal"
        )

    old_meal = await db.get(Meal, meal_id)
    if old_meal:
        await db.delete(old_meal)
        await db.flush()

    new_meal_data = new_meals_data[0]
    new_meal_data["day_of_week"] = target_meal.day_of_week
    new_meal_data["meal_type"] = target_meal.meal_type

    name_to_id = _map_profile_name_to_id(profiles)
    meal_plan_obj = await db.get(MealPlan, plan_id)
    await _persist_meals(db, meal_plan_obj, [new_meal_data], name_to_id)
    await db.commit()

    result = await db.execute(
        select(Meal)
        .options(selectinload(Meal.portions), selectinload(Meal.ingredients))
        .where(
            Meal.meal_plan_id == plan_id,
            Meal.day_of_week == target_meal.day_of_week,
            Meal.meal_type == target_meal.meal_type,
        )
        .order_by(Meal.created_at.desc())
        .limit(1)
    )
    new_meal = result.scalar_one_or_none()
    if not new_meal:
        raise HTTPException(
            status_code=500, detail="Failed to retrieve regenerated meal"
        )
    return new_meal


@router.delete("/{plan_id}", status_code=204)
async def delete_meal_plan(
    plan_id: str,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    plan = await db.get(MealPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Meal plan not found")
    await db.delete(plan)
    await db.commit()


async def _get_plan_detail(db: AsyncSession, plan_id: str) -> MealPlan | None:
    result = await db.execute(
        select(MealPlan)
        .options(
            selectinload(MealPlan.meals).selectinload(Meal.portions),
            selectinload(MealPlan.meals).selectinload(Meal.ingredients),
        )
        .where(MealPlan.id == plan_id)
    )
    return result.scalar_one_or_none()
