"""add user identity and employee-store assignments

Revision ID: 8f3d2b7c1a64
Revises: c2a4f691d8b3
Create Date: 2026-10-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8f3d2b7c1a64"
down_revision: Union[str, Sequence[str], None] = "c2a4f691d8b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email", sa.String(), nullable=False))
    op.add_column("users", sa.Column("mobile", sa.String(), nullable=False))
    op.create_unique_constraint("uq_users_email", "users", ["email"])
    op.create_unique_constraint("uq_users_mobile", "users", ["mobile"])
    op.create_unique_constraint(
        "uq_users_employee_id", "users", ["employee_id"]
    )
    op.create_foreign_key(
        "fk_users_employee_id_employees",
        "users",
        "employees",
        ["employee_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_table(
        "employee_stores",
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.PrimaryKeyConstraint("employee_id", "store_id"),
    )


def downgrade() -> None:
    op.drop_table("employee_stores")
    op.drop_constraint(
        "fk_users_employee_id_employees", "users", type_="foreignkey"
    )
    op.drop_constraint("uq_users_employee_id", "users", type_="unique")
    op.drop_constraint("uq_users_mobile", "users", type_="unique")
    op.drop_constraint("uq_users_email", "users", type_="unique")
    op.drop_column("users", "mobile")
    op.drop_column("users", "email")