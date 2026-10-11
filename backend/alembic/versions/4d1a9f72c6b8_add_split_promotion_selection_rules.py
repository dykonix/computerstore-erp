"""add split promotion selection rules

Revision ID: 4d1a9f72c6b8
Revises: 8c3d7a21f406
Create Date: 2026-10-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4d1a9f72c6b8"
down_revision: Union[str, Sequence[str], None] = "8c3d7a21f406"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sale_items",
        sa.Column("promotion_benefit_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "sale_items",
        sa.Column("promotion_benefit_name", sa.String(), nullable=True),
    )
    op.add_column(
        "sale_items",
        sa.Column("promotion_source_sale_item_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_sale_items_promotion_source_sale_item",
        "sale_items",
        "sale_items",
        ["promotion_source_sale_item_id"],
        ["id"],
    )
    op.add_column(
        "sale_items",
        sa.Column(
            "is_promotion_benefit",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.create_unique_constraint(
        "uq_sale_items_sale_promotion_benefit",
        "sale_items",
        ["sale_id", "promotion_source_sale_item_id", "promotion_benefit_id"],
    )
    op.create_check_constraint(
        "ck_sale_items_promotion_benefit_metadata",
        "sale_items",
        "(is_promotion_benefit = false AND promotion_benefit_id IS NULL "
        "AND promotion_source_sale_item_id IS NULL) OR "
        "(is_promotion_benefit = true AND promotion_benefit_id IS NOT NULL "
        "AND promotion_benefit_name IS NOT NULL "
        "AND promotion_source_sale_item_id IS NOT NULL)",
    )
    op.add_column(
        "promotion_groups",
        sa.Column("group_requirement", sa.String(), nullable=True),
    )
    op.add_column(
        "promotion_groups",
        sa.Column("benefit_selection_rule", sa.String(), nullable=True),
    )
    op.create_check_constraint(
        "ck_promotion_groups_group_requirement",
        "promotion_groups",
        "group_requirement IS NULL OR group_requirement IN ('REQUIRED', 'OPTIONAL')",
    )
    op.create_check_constraint(
        "ck_promotion_groups_benefit_selection_rule",
        "promotion_groups",
        "benefit_selection_rule IS NULL OR benefit_selection_rule IN ('ONE', 'ANY', 'ALL')",
    )
    op.create_check_constraint(
        "ck_promotion_groups_split_rules_paired",
        "promotion_groups",
        "(group_requirement IS NULL AND benefit_selection_rule IS NULL) OR "
        "(group_requirement IS NOT NULL AND benefit_selection_rule IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_sale_items_promotion_benefit_metadata",
        "sale_items",
        type_="check",
    )
    op.drop_constraint(
        "ck_promotion_groups_split_rules_paired",
        "promotion_groups",
        type_="check",
    )
    op.drop_constraint(
        "uq_sale_items_sale_promotion_benefit",
        "sale_items",
        type_="unique",
    )
    op.drop_constraint(
        "fk_sale_items_promotion_source_sale_item",
        "sale_items",
        type_="foreignkey",
    )
    op.drop_column("sale_items", "promotion_source_sale_item_id")
    op.drop_column("sale_items", "is_promotion_benefit")
    op.drop_column("sale_items", "promotion_benefit_name")
    op.drop_column("sale_items", "promotion_benefit_id")
    op.drop_constraint(
        "ck_promotion_groups_benefit_selection_rule",
        "promotion_groups",
        type_="check",
    )
    op.drop_constraint(
        "ck_promotion_groups_group_requirement",
        "promotion_groups",
        type_="check",
    )
    op.drop_column("promotion_groups", "benefit_selection_rule")
    op.drop_column("promotion_groups", "group_requirement")