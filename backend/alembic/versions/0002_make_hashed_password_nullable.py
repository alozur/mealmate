"""make hashed_password nullable for authelia auto-provisioned users

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-28

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "mealmate"


def upgrade() -> None:
    """Allow hashed_password to be NULL so Authelia-provisioned users work."""
    op.alter_column(
        "users",
        "hashed_password",
        existing_type=sa.String(255),
        nullable=True,
        schema=SCHEMA,
    )


def downgrade() -> None:
    """Revert hashed_password back to NOT NULL."""
    op.alter_column(
        "users",
        "hashed_password",
        existing_type=sa.String(255),
        nullable=False,
        schema=SCHEMA,
    )
