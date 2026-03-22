"""initial schema - all tables

Revision ID: 0001
Revises:
Create Date: 2026-03-22

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "mealmate"


def upgrade() -> None:
    """Create all tables."""
    # users
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        schema=SCHEMA,
    )

    # profiles
    op.create_table(
        "profiles",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("goal", sa.String(50), nullable=False),
        sa.Column("restrictions", sa.Text(), nullable=True),
        sa.Column("calorie_target", sa.Integer(), nullable=False),
        sa.Column("protein_target", sa.Integer(), nullable=False),
        sa.Column("carbs_target", sa.Integer(), nullable=False),
        sa.Column("fat_target", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=True, unique=True),
        sa.ForeignKeyConstraint(["user_id"], ["mealmate.users.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )

    # meal_plans
    op.create_table(
        "meal_plans",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("week_end", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )

    # meals
    op.create_table(
        "meals",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("meal_plan_id", sa.String(36), nullable=False),
        sa.ForeignKeyConstraint(
            ["meal_plan_id"], ["mealmate.meal_plans.id"], ondelete="CASCADE"
        ),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("meal_type", sa.String(20), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("recipe_steps", sa.Text(), nullable=True),
        sa.Column("prep_time_min", sa.Integer(), nullable=True),
        sa.Column("cook_time_min", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )

    # meal_portions
    op.create_table(
        "meal_portions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("meal_id", sa.String(36), nullable=False),
        sa.Column("profile_id", sa.String(36), nullable=False),
        sa.ForeignKeyConstraint(
            ["meal_id"], ["mealmate.meals.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["profile_id"], ["mealmate.profiles.id"]),
        sa.Column("serving_size", sa.String(100), nullable=False),
        sa.Column("calories", sa.Integer(), nullable=False),
        sa.Column("protein_g", sa.Numeric(6, 1), nullable=False),
        sa.Column("carbs_g", sa.Numeric(6, 1), nullable=False),
        sa.Column("fat_g", sa.Numeric(6, 1), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )

    # ingredients
    op.create_table(
        "ingredients",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("meal_id", sa.String(36), nullable=False),
        sa.ForeignKeyConstraint(
            ["meal_id"], ["mealmate.meals.id"], ondelete="CASCADE"
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("quantity", sa.String(50), nullable=False),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )

    # inventory_items
    op.create_table(
        "inventory_items",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("quantity", sa.String(50), nullable=True),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("storage_location", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )


def downgrade() -> None:
    """Drop all tables in reverse dependency order."""
    op.drop_table("inventory_items", schema=SCHEMA)
    op.drop_table("ingredients", schema=SCHEMA)
    op.drop_table("meal_portions", schema=SCHEMA)
    op.drop_table("meals", schema=SCHEMA)
    op.drop_table("meal_plans", schema=SCHEMA)
    op.drop_table("profiles", schema=SCHEMA)
    op.drop_table("users", schema=SCHEMA)
