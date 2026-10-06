"""add role permission scopes

Revision ID: b71d4c9e2a10
Revises: 8f3d2b7c1a64
Create Date: 2026-10-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b71d4c9e2a10"
down_revision: Union[str, Sequence[str], None] = "8f3d2b7c1a64"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "role_permissions",
        sa.Column(
            "scope",
            sa.String(),
            nullable=False,
            server_default=sa.text("'assigned_stores'"),
        ),
    )
    op.create_check_constraint(
        "ck_role_permissions_scope",
        "role_permissions",
        "scope IN ('assigned_stores', 'all_tenant_stores')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_role_permissions_scope", "role_permissions", type_="check"
    )
    op.drop_column("role_permissions", "scope")