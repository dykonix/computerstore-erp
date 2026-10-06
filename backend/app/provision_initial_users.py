"""Provision the initial Admin and Sales users interactively.

Run from ``backend`` with ``python -m app.provision_initial_users``. Passwords
are read with terminal echo disabled and are never written to the database or logs.
"""

from getpass import getpass
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.employee_store import EmployeeStore
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.store import Store
from app.models.tenant import Tenant
from app.models.user import User
from app.models.user_role import UserRole
from app.security.password import hash_password, verify_password
from app.services.authorization_service import (
    ALL_PERMISSION,
    ALL_TENANT_STORES,
    ASSIGNED_STORES,
    AuthorizationService,
    PermissionDeniedError,
)
from app.services.auth_service import AuthService, InvalidCredentialsError
from app.schemas.auth import LoginRequest


TENANT_NAME = "Mahamaya Computers"
ADMIN_EMAIL = "dykonix@gmail.com"
ADMIN_MOBILE = "7290003990"
SALES_EMAIL = "technomanojt@gmail.com"
SALES_MOBILE = "9810533117"
ADMIN_EMPLOYEE_EMAIL = "dykonix@gmail.com"
SALES_EMPLOYEE_NAME = "Techno Manoj"
SALES_STORE_NAME = "HP World SBP"
REQUIRED_GRANTS = {
    "Admin": (ALL_PERMISSION, ASSIGNED_STORES),
    "Sales": ("sell", ASSIGNED_STORES),
    "Sales Global": ("sell", ALL_TENANT_STORES),
}


class ProvisioningConflict(Exception):
    pass


def _single_or_conflict(records: list[User], identity: str) -> User | None:
    distinct = {record.id: record for record in records}
    if len(distinct) > 1:
        raise ProvisioningConflict(f"Conflicting User records match {identity}")
    return next(iter(distinct.values()), None)


def _find_user(
    session: Session,
    *,
    email: str,
    mobile: str,
    employee_id: int,
    tenant_id: int,
) -> User | None:
    matches = []
    for column, value, label in (
        (User.email, email, "email"),
        (User.mobile, mobile, "mobile"),
        (User.employee_id, employee_id, "employee"),
    ):
        match = session.scalar(select(User).where(column == value))
        if match is not None:
            if match.tenant_id != tenant_id:
                raise ProvisioningConflict(
                    f"A User matched by {label} belongs to a different tenant"
                )
            matches.append(match)
    selected = _single_or_conflict(matches, email)
    if selected is not None and (
        selected.email != email
        or selected.mobile != mobile
        or selected.employee_id != employee_id
        or not selected.is_active
    ):
        raise ProvisioningConflict(
            f"Existing User for {email} conflicts with the requested identity"
        )
    return selected


def _get_role(session: Session, tenant_id: int, name: str) -> Role:
    role = session.scalar(
        select(Role).where(Role.tenant_id == tenant_id, Role.name == name)
    )
    if role is None or not role.is_active:
        raise ProvisioningConflict(f"Required active role is missing: {name}")
    expected_code, expected_scope = REQUIRED_GRANTS[name]
    permission = session.scalar(
        select(Permission).where(Permission.code == expected_code)
    )
    if permission is None:
        raise ProvisioningConflict(f"Required permission is missing: {expected_code}")
    grant = session.get(
        RolePermission,
        {"role_id": role.id, "permission_id": permission.id},
    )
    if grant is None or grant.scope != expected_scope:
        raise ProvisioningConflict(f"Required grant is missing or mismatched for {name}")
    return role


def _ensure_user_role(
    session: Session, user: User, expected_role: Role
) -> None:
    assignments = list(
        session.scalars(select(UserRole).where(UserRole.user_id == user.id))
    )
    role_ids = {assignment.role_id for assignment in assignments}
    if role_ids - {expected_role.id}:
        raise ProvisioningConflict(
            f"Existing role assignments conflict for {user.email}"
        )
    if expected_role.id not in role_ids:
        session.add(UserRole(user_id=user.id, role_id=expected_role.id))
        session.flush()


def _ensure_user(
    session: Session,
    *,
    tenant_id: int,
    employee: Employee,
    email: str,
    mobile: str,
    password: str,
    role: Role,
) -> User:
    user = _find_user(
        session,
        email=email,
        mobile=mobile,
        employee_id=employee.id,
        tenant_id=tenant_id,
    )
    if user is None:
        user = User(
            tenant_id=tenant_id,
            username=email,
            password_hash=hash_password(password),
            email=email,
            mobile=mobile,
            employee_id=employee.id,
            is_active=True,
        )
        session.add(user)
        session.flush()
    elif not verify_password(password, user.password_hash):
        raise ProvisioningConflict(
            f"Existing User for {email} has different credentials; no password was changed"
        )
    _ensure_user_role(session, user, role)
    return user


def provision(admin_password: str, sales_password: str) -> dict[str, int]:
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    engine = create_engine(database_url)
    try:
        with Session(engine) as session, session.begin():
            tenant = session.scalar(
                select(Tenant).where(Tenant.id == 1, Tenant.name == TENANT_NAME)
            )
            if tenant is None or not tenant.is_active:
                raise ProvisioningConflict("Expected active tenant 1 was not found")

            admin_employee = session.scalar(
                select(Employee).where(
                    Employee.id == 1,
                    Employee.tenant_id == tenant.id,
                    Employee.email == ADMIN_EMPLOYEE_EMAIL,
                )
            )
            if admin_employee is None or not admin_employee.is_active:
                raise ProvisioningConflict("Expected active Dykonix Employee was not found")

            matching_sales_employees = list(
                session.scalars(
                    select(Employee).where(Employee.email == SALES_EMAIL)
                )
            )
            if any(employee.tenant_id != tenant.id for employee in matching_sales_employees):
                raise ProvisioningConflict(
                    "Sales Employee identity already exists in a different tenant"
                )
            if len(matching_sales_employees) > 1:
                raise ProvisioningConflict("Multiple Sales Employee records match the identity")
            sales_employee = matching_sales_employees[0] if matching_sales_employees else None
            if sales_employee is None:
                sales_employee = Employee(
                    tenant_id=tenant.id,
                    email=SALES_EMAIL,
                    name=SALES_EMPLOYEE_NAME,
                    is_active=True,
                )
                session.add(sales_employee)
                session.flush()
            elif not sales_employee.is_active or sales_employee.name not in (
                None,
                SALES_EMPLOYEE_NAME,
            ):
                raise ProvisioningConflict("Existing Sales Employee conflicts with requested identity")
            elif sales_employee.name is None:
                sales_employee.name = SALES_EMPLOYEE_NAME
                session.flush()

            stores = {}
            for store_name in ("Mahamaya Computers", "HP World SBP", "HP World JSG"):
                matches = list(
                    session.scalars(
                        select(Store).where(
                            Store.tenant_id == tenant.id, Store.name == store_name
                        )
                    )
                )
                if len(matches) != 1 or not matches[0].is_active:
                    raise ProvisioningConflict(
                        f"Expected one active Store named {store_name} in tenant 1"
                    )
                stores[store_name] = matches[0]

            admin_role = _get_role(session, tenant.id, "Admin")
            sales_role = _get_role(session, tenant.id, "Sales")
            _get_role(session, tenant.id, "Sales Global")

            admin = _ensure_user(
                session,
                tenant_id=tenant.id,
                employee=admin_employee,
                email=ADMIN_EMAIL,
                mobile=ADMIN_MOBILE,
                password=admin_password,
                role=admin_role,
            )
            sales = _ensure_user(
                session,
                tenant_id=tenant.id,
                employee=sales_employee,
                email=SALES_EMAIL,
                mobile=SALES_MOBILE,
                password=sales_password,
                role=sales_role,
            )

            sales_assignments = list(
                session.scalars(
                    select(EmployeeStore).where(
                        EmployeeStore.employee_id == sales_employee.id
                    )
                )
            )
            expected_sales_store_id = stores[SALES_STORE_NAME].id
            if any(item.store_id != expected_sales_store_id for item in sales_assignments):
                raise ProvisioningConflict(
                    "Sales Employee has existing Store assignments outside HP World SBP"
                )
            if not any(
                item.store_id == expected_sales_store_id for item in sales_assignments
            ):
                session.add(
                    EmployeeStore(
                        employee_id=sales_employee.id,
                        store_id=expected_sales_store_id,
                    )
                )
                session.flush()

            return {"admin_user_id": admin.id, "sales_user_id": sales.id}
    finally:
        engine.dispose()


def main() -> None:
    admin_password = getpass("Admin password (hidden): ")
    sales_password = getpass("Sales password (hidden): ")
    if not admin_password or not sales_password:
        raise SystemExit("Passwords must not be empty")
    result = provision(admin_password, sales_password)
    print(
        "Provisioning completed. "
        f"Admin User ID: {result['admin_user_id']}; "
        f"Sales User ID: {result['sales_user_id']}."
    )


if __name__ == "__main__":
    main()
