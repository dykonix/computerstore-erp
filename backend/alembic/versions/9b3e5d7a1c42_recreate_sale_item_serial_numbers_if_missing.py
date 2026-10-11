"""recreate sale_item_serial_numbers where the earlier migration was stamped but never ran

Revision ID: 9b3e5d7a1c42
Revises: 7a2c4e91d603
Create Date: 2026-10-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9b3e5d7a1c42"
down_revision: Union[str, Sequence[str], None] = "7a2c4e91d603"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # IF NOT EXISTS makes this a no-op where ccfb568af5bb already created the table.
    op.create_table(
        "sale_item_serial_numbers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sale_item_id", sa.Integer(), nullable=False),
        sa.Column("product_serial_number_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["sale_item_id"], ["sale_items.id"]),
        sa.ForeignKeyConstraint(
            ["product_serial_number_id"], ["product_serial_numbers.id"]
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "sale_item_id",
            "product_serial_number_id",
            name="uq_sale_item_serial_number_pair",
        ),
        sa.UniqueConstraint(
            "product_serial_number_id",
            name="uq_sale_item_serial_number_serial",
        ),
        if_not_exists=True,
    )


def downgrade() -> None:
    # The table is owned by ccfb568af5bb; dropping it here would break that revision's downgrade.
    pass
