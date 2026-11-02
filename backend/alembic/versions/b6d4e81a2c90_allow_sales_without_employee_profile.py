"""Allow sales to be created without a separate employee profile.

Revision ID: b6d4e81a2c90
Revises: 3d23d9650f89
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b6d4e81a2c90"
down_revision: Union[str, Sequence[str], None] = "3d23d9650f89"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "sales",
        "employee_id",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    # Existing rows must be assigned an employee before reversing this change.
    op.alter_column(
        "sales",
        "employee_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
