import json
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Profile schemas
# ---------------------------------------------------------------------------


class ProfileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    goal: str = Field(..., min_length=1, max_length=50)
    restrictions: list[str] = []
    calorie_target: int = Field(default=2000, ge=500, le=10000)
    protein_target: int = Field(default=150, ge=0, le=1000)
    carbs_target: int = Field(default=200, ge=0, le=1000)
    fat_target: int = Field(default=70, ge=0, le=500)


class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    goal: str | None = Field(default=None, min_length=1, max_length=50)
    restrictions: list[str] | None = None
    calorie_target: int | None = Field(default=None, ge=500, le=10000)
    protein_target: int | None = Field(default=None, ge=0, le=1000)
    carbs_target: int | None = Field(default=None, ge=0, le=1000)
    fat_target: int | None = Field(default=None, ge=0, le=500)


class ProfileResponse(BaseModel):
    id: str
    name: str
    goal: str
    restrictions: list[str]
    calorie_target: int
    protein_target: int
    carbs_target: int
    fat_target: int
    created_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def parse_restrictions(cls, data: object) -> object:
        if hasattr(data, "restrictions") and isinstance(data.restrictions, str):
            try:
                data.restrictions = json.loads(data.restrictions)
            except (json.JSONDecodeError, TypeError):
                data.restrictions = []
        elif hasattr(data, "restrictions") and data.restrictions is None:
            data.restrictions = []
        return data


# ---------------------------------------------------------------------------
# Meal Plan schemas
# ---------------------------------------------------------------------------


class MealPlanGenerate(BaseModel):
    week_start: date | None = None


class MealPortionResponse(BaseModel):
    id: str
    profile_id: str
    serving_size: str
    calories: int
    protein_g: Decimal
    carbs_g: Decimal
    fat_g: Decimal

    model_config = {"from_attributes": True}


class IngredientResponse(BaseModel):
    id: str
    name: str
    quantity: str
    unit: str | None
    category: str

    model_config = {"from_attributes": True}


class MealResponse(BaseModel):
    id: str
    day_of_week: int
    meal_type: str
    name: str
    description: str | None
    recipe_steps: list[str]
    prep_time_min: int | None
    cook_time_min: int | None
    portions: list[MealPortionResponse] = []
    ingredients: list[IngredientResponse] = []

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def parse_recipe_steps(cls, data: object) -> object:
        if hasattr(data, "recipe_steps") and isinstance(data.recipe_steps, str):
            try:
                data.recipe_steps = json.loads(data.recipe_steps)
            except (json.JSONDecodeError, TypeError):
                data.recipe_steps = []
        elif hasattr(data, "recipe_steps") and data.recipe_steps is None:
            data.recipe_steps = []
        return data


class MealPlanResponse(BaseModel):
    id: str
    week_start: date
    week_end: date
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MealPlanDetailResponse(MealPlanResponse):
    meals: list[MealResponse] = []


# ---------------------------------------------------------------------------
# Shopping List schemas
# ---------------------------------------------------------------------------


class ShoppingListItem(BaseModel):
    name: str
    total_quantity: str
    unit: str | None
    category: str


class ShoppingListResponse(BaseModel):
    categories: dict[str, list[ShoppingListItem]]


# ---------------------------------------------------------------------------
# Common schemas
# ---------------------------------------------------------------------------


class MessageResponse(BaseModel):
    message: str
