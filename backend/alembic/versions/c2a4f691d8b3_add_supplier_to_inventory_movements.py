"""add supplier to inventory movements

Revision ID: c2a4f691d8b3
Revises: 109e67269602
Create Date: 2026-10-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c2a4f691d8b3"
down_revision: Union[str, Sequence[str], None] = "109e67269602"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "inventory_movements",
        sa.Column("supplier_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_inventory_movements_supplier_id_suppliers",
        "inventory_movements",
        "suppliers",
        ["supplier_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_inventory_movements_supplier_id_suppliers",
        "inventory_movements",
        type_="foreignkey",
    )
    op.drop_column("inventory_movements", "supplier_id")
