from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Meal, MealPlan
from app.schemas import ShoppingListItem, ShoppingListResponse

router = APIRouter(prefix="/api/meal-plans", tags=["shopping"])


@router.get("/{plan_id}/shopping-list", response_model=ShoppingListResponse)
async def get_shopping_list(plan_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MealPlan)
        .options(selectinload(MealPlan.meals).selectinload(Meal.ingredients))
        .where(MealPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Meal plan not found")

    aggregated: dict[tuple[str, str | None, str], list[str]] = defaultdict(list)

    for meal in plan.meals:
        for ing in meal.ingredients:
            key = (ing.name.lower().strip(), ing.unit, ing.category)
            aggregated[key].append(ing.quantity)

    categories: dict[str, list[ShoppingListItem]] = defaultdict(list)

    for (name, unit, category), quantities in sorted(aggregated.items()):
        total = _aggregate_quantities(quantities)
        categories[category].append(
            ShoppingListItem(
                name=name.title(),
                total_quantity=total,
                unit=unit,
                category=category,
            )
        )

    return ShoppingListResponse(categories=dict(categories))


def _aggregate_quantities(quantities: list[str]) -> str:
    total = 0.0
    non_numeric = []
    for q in quantities:
        try:
            total += float(q)
        except (ValueError, TypeError):
            non_numeric.append(q)

    if non_numeric and total == 0:
        return ", ".join(non_numeric)
    elif non_numeric:
        parts = [str(total)] + non_numeric
        return " + ".join(parts)
    else:
        if total == int(total):
            return str(int(total))
        return f"{total:.1f}"
