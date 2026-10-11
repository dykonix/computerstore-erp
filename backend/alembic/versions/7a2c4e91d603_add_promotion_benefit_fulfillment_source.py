"""add promotion benefit fulfillment source

Revision ID: 7a2c4e91d603
Revises: 4d1a9f72c6b8
Create Date: 2026-10-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7a2c4e91d603"
down_revision: Union[str, Sequence[str], None] = "4d1a9f72c6b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_PROMOTION_BENEFIT_METADATA_CHECK = """(is_promotion_benefit = false
    AND promotion_benefit_id IS NULL
    AND promotion_source_sale_item_id IS NULL
    AND promotion_benefit_source IS NULL)
OR (is_promotion_benefit = true
    AND promotion_benefit_id IS NOT NULL
    AND promotion_benefit_name IS NOT NULL
    AND promotion_source_sale_item_id IS NOT NULL
    AND promotion_benefit_source IN ('STORE', 'MANUFACTURER'))"""


_OLD_PROMOTION_BENEFIT_METADATA_CHECK = """(is_promotion_benefit = false
    AND promotion_benefit_id IS NULL
    AND promotion_source_sale_item_id IS NULL)
OR (is_promotion_benefit = true
    AND promotion_benefit_id IS NOT NULL
    AND promotion_benefit_name IS NOT NULL
    AND promotion_source_sale_item_id IS NOT NULL)"""


def upgrade() -> None:
    op.drop_constraint(
        "ck_sale_items_promotion_benefit_metadata",
        "sale_items",
        type_="check",
    )
    op.add_column(
        "sale_items",
        sa.Column("promotion_benefit_source", sa.String(), nullable=True),
    )
    op.execute(
        "UPDATE sale_items SET promotion_benefit_source = 'MANUFACTURER' "
        "WHERE is_promotion_benefit = true"
    )
    op.create_check_constraint(
        "ck_sale_items_promotion_benefit_metadata",
        "sale_items",
        _PROMOTION_BENEFIT_METADATA_CHECK,
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_sale_items_promotion_benefit_metadata",
        "sale_items",
        type_="check",
    )
    op.create_check_constraint(
        "ck_sale_items_promotion_benefit_metadata",
        "sale_items",
        _OLD_PROMOTION_BENEFIT_METADATA_CHECK,
    )
    op.drop_column("sale_items", "promotion_benefit_source")
