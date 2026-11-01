from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user_role import UserRole


class RoleRepository:
    def list_roles(self, session: Session, tenant_id: int) -> list[Role]:
        return list(
            session.scalars(
                select(Role)
                .where(Role.tenant_id == tenant_id)
                .order_by(Role.name, Role.id)
            )
        )

    def get_role(
        self, session: Session, tenant_id: int, role_id: int
    ) -> Role | None:
        return session.scalar(
            select(Role).where(
                Role.id == role_id,
                Role.tenant_id == tenant_id,
            )
        )

    def get_role_by_name(
        self, session: Session, tenant_id: int, name: str
    ) -> Role | None:
        return session.scalar(
            select(Role).where(
                Role.tenant_id == tenant_id,
                Role.name == name,
            )
        )

    def list_permissions(self, session: Session) -> list[Permission]:
        return list(
            session.scalars(
                select(Permission)
                .where(Permission.code.notin_(["ALL", "permissions.manage"]))
                .order_by(Permission.code)
            )
        )

    def list_role_permissions(
        self, session: Session, role_id: int
    ) -> list[tuple[str, str | None, str]]:
        return list(
            session.execute(
                select(Permission.code, Permission.description, RolePermission.scope)
                .join(RolePermission, RolePermission.permission_id == Permission.id)
                .where(RolePermission.role_id == role_id)
                .order_by(Permission.code)
            ).all()
        )

    def role_has_all_permission(self, session: Session, role_id: int) -> bool:
        return session.scalar(
            select(RolePermission.role_id)
            .join(Permission, Permission.id == RolePermission.permission_id)
            .where(
                RolePermission.role_id == role_id,
                Permission.code == "ALL",
            )
        ) is not None

    def create_role(self, session: Session, role: Role) -> Role:
        session.add(role)
        session.flush()
        return role

    def user_has_role(self, session: Session, user_id: int, role_id: int) -> bool:
        return session.scalar(
            select(UserRole.user_id).where(
                UserRole.user_id == user_id,
                UserRole.role_id == role_id,
            )
        ) is not None
