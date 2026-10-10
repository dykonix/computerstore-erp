"""add sale item pricing flags

Revision ID: 6506048193bc
Revises: a21d7c9e4b10
Create Date: 2026-10-08 08:11:03.405383
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "6506048193bc"
down_revision: Union[str, Sequence[str], None] = "a21d7c9e4b10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add pricing and free-product fields to sale items."""

    op.add_column(
        "sale_items",
        sa.Column(
            "configured_minimum_price",
            sa.Numeric(precision=12, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )

    op.add_column(
        "sale_items",
        sa.Column(
            "minimum_price_override",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )

    op.add_column(
        "sale_items",
        sa.Column(
            "is_free_product",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Remove pricing and free-product fields from sale items."""

    op.drop_column("sale_items", "is_free_product")
    op.drop_column("sale_items", "minimum_price_override")
    op.drop_column("sale_items", "configured_minimum_price")