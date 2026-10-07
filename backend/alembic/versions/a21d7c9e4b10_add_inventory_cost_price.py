"""add inventory cost price

Revision ID: a21d7c9e4b10
Revises: ccfb568af5bb
Create Date: 2026-10-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a21d7c9e4b10"
down_revision: Union[str, Sequence[str], None] = "ccfb568af5bb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "inventory",
        sa.Column(
            "cost_price",
            sa.Numeric(precision=12, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_inventory_cost_price_nonnegative", "inventory", "cost_price >= 0"
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_inventory_cost_price_nonnegative", "inventory", type_="check"
    )
    op.drop_column("inventory", "cost_price")