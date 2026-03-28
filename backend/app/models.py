import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    profile: Mapped["Profile | None"] = relationship(back_populates="user")


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    goal: Mapped[str] = mapped_column(String(50), nullable=False)
    restrictions: Mapped[str | None] = mapped_column(Text, nullable=True)
    calorie_target: Mapped[int] = mapped_column(Integer, nullable=False, default=2000)
    protein_target: Mapped[int] = mapped_column(Integer, nullable=False, default=150)
    carbs_target: Mapped[int] = mapped_column(Integer, nullable=False, default=200)
    fat_target: Mapped[int] = mapped_column(Integer, nullable=False, default=70)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True, unique=True
    )

    user: Mapped["User | None"] = relationship(back_populates="profile")
    meal_portions: Mapped[list["MealPortion"]] = relationship(back_populates="profile")


class MealPlan(Base):
    __tablename__ = "meal_plans"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    week_end: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    meals: Mapped[list["Meal"]] = relationship(
        back_populates="meal_plan", cascade="all, delete-orphan"
    )


class Meal(Base):
    __tablename__ = "meals"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    meal_plan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meal_plans.id", ondelete="CASCADE"), nullable=False
    )
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    meal_type: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    recipe_steps: Mapped[str | None] = mapped_column(Text, nullable=True)
    prep_time_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cook_time_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    meal_plan: Mapped[MealPlan] = relationship(back_populates="meals")
    portions: Mapped[list["MealPortion"]] = relationship(
        back_populates="meal", cascade="all, delete-orphan"
    )
    ingredients: Mapped[list["Ingredient"]] = relationship(
        back_populates="meal", cascade="all, delete-orphan"
    )


class MealPortion(Base):
    __tablename__ = "meal_portions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    meal_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meals.id", ondelete="CASCADE"), nullable=False
    )
    profile_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("profiles.id"), nullable=False
    )
    serving_size: Mapped[str] = mapped_column(String(100), nullable=False)
    calories: Mapped[int] = mapped_column(Integer, nullable=False)
    protein_g: Mapped[Decimal] = mapped_column(Numeric(6, 1), nullable=False)
    carbs_g: Mapped[Decimal] = mapped_column(Numeric(6, 1), nullable=False)
    fat_g: Mapped[Decimal] = mapped_column(Numeric(6, 1), nullable=False)

    meal: Mapped[Meal] = relationship(back_populates="portions")
    profile: Mapped[Profile] = relationship(back_populates="meal_portions")


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    meal_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meals.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[str] = mapped_column(String(50), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="pantry")

    meal: Mapped[Meal] = relationship(back_populates="ingredients")


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="other")
    storage_location: Mapped[str] = mapped_column(
        String(20), nullable=False, default="fridge"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
