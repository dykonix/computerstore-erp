"""add selected sale promotions and cashback totals

Revision ID: 8c3d7a21f406
Revises: 756cb1b2d574
Create Date: 2026-10-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "8c3d7a21f406"
down_revision: Union[str, Sequence[str], None] = "756cb1b2d574"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sales",
        sa.Column(
            "payable_amount",
            sa.Numeric(precision=12, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.execute(
        "UPDATE sales SET payable_amount = GREATEST(total_amount - gst_amount, 0)"
    )
    op.create_check_constraint(
        "ck_sales_payable_amount_nonnegative",
        "sales",
        "payable_amount >= 0",
    )
    op.add_column(
        "sales",
        sa.Column(
            "cashback_amount",
            sa.Numeric(precision=12, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_sales_cashback_amount_nonnegative",
        "sales",
        "cashback_amount >= 0",
    )
    op.add_column(
        "sale_items",
        sa.Column("promotion_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "sale_items",
        sa.Column("promotion_name", sa.String(), nullable=True),
    )
    op.add_column(
        "sale_items",
        sa.Column(
            "promotion_cashback_amount",
            sa.Numeric(precision=12, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.create_foreign_key(
        "fk_sale_items_promotion_id_promotions",
        "sale_items",
        "promotions",
        ["promotion_id"],
        ["id"],
    )
    op.create_check_constraint(
        "ck_sale_items_promotion_cashback_nonnegative",
        "sale_items",
        "promotion_cashback_amount >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_sale_items_promotion_cashback_nonnegative",
        "sale_items",
        type_="check",
    )
    op.drop_constraint(
        "fk_sale_items_promotion_id_promotions",
        "sale_items",
        type_="foreignkey",
    )
    op.drop_column("sale_items", "promotion_cashback_amount")
    op.drop_column("sale_items", "promotion_name")
    op.drop_column("sale_items", "promotion_id")
    op.drop_constraint(
        "ck_sales_payable_amount_nonnegative",
        "sales",
        type_="check",
    )
    op.drop_column("sales", "payable_amount")
    op.drop_constraint(
        "ck_sales_cashback_amount_nonnegative",
        "sales",
        type_="check",
    )
    op.drop_column("sales", "cashback_amount")