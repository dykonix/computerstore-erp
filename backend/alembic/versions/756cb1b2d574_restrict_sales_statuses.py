"""restrict sales statuses

Revision ID: 756cb1b2d574
Revises: 6506048193bc
Create Date: 2026-10-08 08:17:48.663765

"""

from typing import Sequence, Union

from alembic import op


revision: str = "756cb1b2d574"
down_revision: Union[str, Sequence[str], None] = "6506048193bc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_sales_status",
        "sales",
        type_="check",
    )

    op.create_check_constraint(
        "ck_sales_status",
        "sales",
        "status IN ('DRAFT', 'RESERVED', 'CONFIRMED', 'DELIVERED')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_sales_status",
        "sales",
        type_="check",
    )

    op.create_check_constraint(
        "ck_sales_status",
        "sales",
        "status IN ('DRAFT', 'RESERVED', 'CONFIRMED', 'PICKED', 'ASSEMBLY', 'DELIVERED', 'CANCELLED')",
    )