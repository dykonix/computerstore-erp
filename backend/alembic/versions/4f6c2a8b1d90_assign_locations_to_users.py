"""Re-key existing location assignment tables from employees to users.

Revision ID: 4f6c2a8b1d90
Revises: 3d23d9650f89

The existing employee_stores and employee_godowns tables are reused. No new
location-assignment tables are created. Existing assignments are mapped through
users.employee_id where a user link exists; orphan employee assignments are
removed because location access is now granted to users only.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "4f6c2a8b1d90"
down_revision: Union[str, Sequence[str], None] = "3d23d9650f89"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Refuse to discard any assignment that cannot be mapped to a user.
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM employee_stores es
                WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.employee_id = es.employee_id)
            ) THEN
                RAISE EXCEPTION 'Cannot migrate employee_stores: an assignment has no linked user';
            END IF;
        END $$
    """)
    op.drop_constraint("employee_stores_employee_id_fkey", "employee_stores", type_="foreignkey")
    op.drop_constraint("employee_stores_pkey", "employee_stores", type_="primary")
    op.execute("""
        UPDATE employee_stores es SET employee_id = u.id
        FROM users u WHERE u.employee_id = es.employee_id
    """)
    op.alter_column("employee_stores", "employee_id", new_column_name="user_id")
    op.create_primary_key("employee_stores_pkey", "employee_stores", ["user_id", "store_id"])
    op.create_foreign_key(
        "employee_stores_user_id_fkey", "employee_stores", "users",
        ["user_id"], ["id"], ondelete="CASCADE",
    )

    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM employee_godowns eg
                WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.employee_id = eg.employee_id)
            ) THEN
                RAISE EXCEPTION 'Cannot migrate employee_godowns: an assignment has no linked user';
            END IF;
        END $$
    """)
    op.drop_constraint("employee_godowns_employee_id_fkey", "employee_godowns", type_="foreignkey")
    op.drop_constraint("employee_godowns_pkey", "employee_godowns", type_="primary")
    op.execute("""
        UPDATE employee_godowns eg SET employee_id = u.id
        FROM users u WHERE u.employee_id = eg.employee_id
    """)
    op.alter_column("employee_godowns", "employee_id", new_column_name="user_id")
    op.create_primary_key("employee_godowns_pkey", "employee_godowns", ["user_id", "godown_id"])
    op.create_foreign_key(
        "employee_godowns_user_id_fkey", "employee_godowns", "users",
        ["user_id"], ["id"], ondelete="CASCADE",
    )


def downgrade() -> None:
    # Refuse to discard assignments for users without an employee link.
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM employee_stores es
                WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.id = es.user_id AND u.employee_id IS NOT NULL)
            ) THEN
                RAISE EXCEPTION 'Cannot downgrade employee_stores: a user assignment has no employee link';
            END IF;
        END $$
    """)
    op.drop_constraint("employee_stores_user_id_fkey", "employee_stores", type_="foreignkey")
    op.drop_constraint("employee_stores_pkey", "employee_stores", type_="primary")
    op.execute("""
        UPDATE employee_stores es SET user_id = u.employee_id
        FROM users u WHERE u.id = es.user_id
    """)
    op.alter_column("employee_stores", "user_id", new_column_name="employee_id")
    op.create_primary_key("employee_stores_pkey", "employee_stores", ["employee_id", "store_id"])
    op.create_foreign_key(
        "employee_stores_employee_id_fkey", "employee_stores", "employees",
        ["employee_id"], ["id"],
    )

    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM employee_godowns eg
                WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.id = eg.user_id AND u.employee_id IS NOT NULL)
            ) THEN
                RAISE EXCEPTION 'Cannot downgrade employee_godowns: a user assignment has no employee link';
            END IF;
        END $$
    """)
    op.drop_constraint("employee_godowns_user_id_fkey", "employee_godowns", type_="foreignkey")
    op.drop_constraint("employee_godowns_pkey", "employee_godowns", type_="primary")
    op.execute("""
        UPDATE employee_godowns eg SET user_id = u.employee_id
        FROM users u WHERE u.id = eg.user_id
    """)
    op.alter_column("employee_godowns", "user_id", new_column_name="employee_id")
    op.create_primary_key("employee_godowns_pkey", "employee_godowns", ["employee_id", "godown_id"])
    op.create_foreign_key(
        "employee_godowns_employee_id_fkey", "employee_godowns", "employees",
        ["employee_id"], ["id"],
    )
