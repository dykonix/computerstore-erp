"""add sale item serial numbers

Revision ID: ccfb568af5bb
Revises: 9d88012ab467
Create Date: 2026-10-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ccfb568af5bb"
down_revision: Union[str, Sequence[str], None] = "9d88012ab467"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        "sale_item_serial_numbers",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "sale_item_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "product_serial_number_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["sale_item_id"],
            ["sale_items.id"],
        ),
        sa.ForeignKeyConstraint(
            ["product_serial_number_id"],
            ["product_serial_numbers.id"],
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
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_table("sale_item_serial_numbers")