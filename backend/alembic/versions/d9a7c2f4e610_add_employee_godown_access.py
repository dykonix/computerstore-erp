"""add employee godown assignments and location scopes

Revision ID: d9a7c2f4e610
Revises: b71d4c9e2a10
Create Date: 2026-11-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d9a7c2f4e610"
down_revision: Union[str, Sequence[str], None] = "b71d4c9e2a10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "employee_godowns",
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id"), primary_key=True),
        sa.Column("godown_id", sa.Integer(), sa.ForeignKey("godowns.id"), primary_key=True),
    )
    op.drop_constraint("ck_role_permissions_scope", "role_permissions", type_="check")
    op.create_check_constraint(
        "ck_role_permissions_scope",
        "role_permissions",
        "scope IN ('assigned_stores', 'all_tenant_stores', 'assigned_locations', 'all_tenant_locations')",
    )


def downgrade() -> None:
    op.execute(
        "UPDATE role_permissions SET scope = 'assigned_stores' "
        "WHERE scope IN ('assigned_locations', 'all_tenant_locations')"
    )
    op.drop_constraint("ck_role_permissions_scope", "role_permissions", type_="check")
    op.create_check_constraint(
        "ck_role_permissions_scope",
        "role_permissions",
        "scope IN ('assigned_stores', 'all_tenant_stores')",
    )
    op.drop_table("employee_godowns")
