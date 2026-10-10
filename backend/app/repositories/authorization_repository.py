from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.employee_store import EmployeeStore
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.store import Store
from app.models.user import User
from app.models.user_role import UserRole


class AuthorizationRepository:
    def get_user(self, session: Session, user_id: int) -> User | None:
        return session.get(User, user_id)

    def get_role(
        self,
        session: Session,
        tenant_id: int,
        role_id: int,
    ) -> Role | None:
        return session.scalar(
            select(Role).where(
                Role.id == role_id,
                Role.tenant_id == tenant_id,
            )
        )

    def get_permission(
        self,
        session: Session,
        permission_code: str,
    ) -> Permission | None:
        return session.scalar(
            select(Permission).where(
                Permission.code == permission_code,
            )
        )

    def get_user_role(
        self,
        session: Session,
        user_id: int,
        role_id: int,
    ) -> UserRole | None:
        return session.get(
            UserRole,
            {
                "user_id": user_id,
                "role_id": role_id,
            },
        )

    def add_user_role(
        self,
        session: Session,
        user_id: int,
        role_id: int,
    ) -> UserRole:
        assignment = UserRole(
            user_id=user_id,
            role_id=role_id,
        )
        session.add(assignment)
        session.flush()
        return assignment

    def remove_user_role(
        self,
        session: Session,
        assignment: UserRole,
    ) -> None:
        session.delete(assignment)
        session.flush()

    def get_role_permission(
        self,
        session: Session,
        role_id: int,
        permission_id: int,
    ) -> RolePermission | None:
        return session.get(
            RolePermission,
            {
                "role_id": role_id,
                "permission_id": permission_id,
            },
        )

    def add_role_permission(
        self,
        session: Session,
        role_id: int,
        permission_id: int,
        scope: str,
    ) -> RolePermission:
        grant = RolePermission(
            role_id=role_id,
            permission_id=permission_id,
            scope=scope,
        )
        session.add(grant)
        session.flush()
        return grant

    def list_active_user_permission_grants(
        self,
        session: Session,
        user: User,
    ) -> list[tuple[str, str]]:
        statement = (
            select(
                Permission.code,
                RolePermission.scope,
            )
            .join(
                RolePermission,
                RolePermission.permission_id == Permission.id,
            )
            .join(
                Role,
                Role.id == RolePermission.role_id,
            )
            .join(
                UserRole,
                UserRole.role_id == Role.id,
            )
            .where(
                UserRole.user_id == user.id,
                Role.tenant_id == user.tenant_id,
                Role.is_active.is_(True),
            )
        )

        return list(session.execute(statement).all())

    def list_permission_codes(
        self,
        session: Session,
    ) -> list[str]:
        return list(
            session.scalars(
                select(Permission.code).order_by(Permission.code)
            )
        )

    def get_store(
        self,
        session: Session,
        tenant_id: int,
        store_id: int,
    ) -> Store | None:
        return session.scalar(
            select(Store).where(
                Store.id == store_id,
                Store.tenant_id == tenant_id,
            )
        )

    def list_active_tenant_stores(
        self,
        session: Session,
        tenant_id: int,
    ) -> list[Store]:
        statement = (
            select(Store)
            .where(
                Store.tenant_id == tenant_id,
                Store.is_active.is_(True),
            )
            .order_by(Store.name)
        )

        return list(session.scalars(statement))

    def list_employee_stores(
        self,
        session: Session,
        tenant_id: int,
        employee_id: int,
    ) -> list[Store]:
        statement = (
            select(Store)
            .join(
                EmployeeStore,
                EmployeeStore.store_id == Store.id,
            )
            .where(
                Store.tenant_id == tenant_id,
                Store.is_active.is_(True),
                EmployeeStore.employee_id == employee_id,
            )
            .order_by(Store.name)
        )

        return list(session.scalars(statement))

    def get_employee(
        self,
        session: Session,
        tenant_id: int,
        employee_id: int,
    ) -> Employee | None:
        return session.scalar(
            select(Employee).where(
                Employee.id == employee_id,
                Employee.tenant_id == tenant_id,
            )
        )

    def employee_has_store(
        self,
        session: Session,
        employee_id: int,
        store_id: int,
    ) -> bool:
        return session.scalar(
            select(EmployeeStore.employee_id).where(
                EmployeeStore.employee_id == employee_id,
                EmployeeStore.store_id == store_id,
            )
        ) is not None