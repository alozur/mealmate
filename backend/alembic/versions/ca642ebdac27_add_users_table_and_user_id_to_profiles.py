"""add users table and user_id to profiles

Revision ID: ca642ebdac27
Revises: 
Create Date: 2026-03-21 18:40:56.573217

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ca642ebdac27'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create users table and add user_id FK to profiles."""
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        schema="mealmate",
    )
    op.add_column(
        "profiles",
        sa.Column("user_id", sa.String(36), nullable=True),
        schema="mealmate",
    )
    op.create_foreign_key(
        "fk_profiles_user_id",
        "profiles",
        "users",
        ["user_id"],
        ["id"],
        source_schema="mealmate",
        referent_schema="mealmate",
    )
    op.create_unique_constraint(
        "uq_profiles_user_id",
        "profiles",
        ["user_id"],
        schema="mealmate",
    )


def downgrade() -> None:
    """Remove user_id from profiles and drop users table."""
    op.drop_constraint(
        "uq_profiles_user_id", "profiles", schema="mealmate", type_="unique"
    )
    op.drop_constraint(
        "fk_profiles_user_id", "profiles", schema="mealmate", type_="foreignkey"
    )
    op.drop_column("profiles", "user_id", schema="mealmate")
    op.drop_table("users", schema="mealmate")
