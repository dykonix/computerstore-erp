from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.repositories.role_repository import RoleRepository
from app.schemas.role import RoleCreate, RolePermissionGrantInput, RoleUpdate
from app.services.authorization_service import ALL_PERMISSION, SUPPORTED_SCOPES


class RoleManagementError(Exception):
    pass


class RoleNotFoundError(Exception):
    pass


class RoleManagementService:
    def __init__(self, repository: RoleRepository | None = None) -> None:
        self.repository = repository or RoleRepository()

    def create_role(
        self, session: Session, tenant_id: int, request: RoleCreate
    ) -> Role:
        name = request.name.strip()
        if not name:
            raise RoleManagementError("Role name is required")
        with session.begin():
            if self.repository.get_role_by_name(session, tenant_id, name):
                raise RoleManagementError("A role with this name already exists")
            return self.repository.create_role(
                session,
                Role(
                    tenant_id=tenant_id,
                    name=name,
                    description=request.description.strip() if request.description else None,
                ),
            )

    def update_role(
        self, session: Session, tenant_id: int, role_id: int, request: RoleUpdate
    ) -> Role:
        updates = request.model_dump(exclude_unset=True)
        if not updates:
            raise RoleManagementError("At least one field must be provided")
        if "is_active" in updates and updates["is_active"] is None:
            raise RoleManagementError("Role active status cannot be empty")
        if "name" in updates:
            if updates["name"] is None or not updates["name"].strip():
                raise RoleManagementError("Role name is required")
            updates["name"] = updates["name"].strip()
        if "description" in updates and updates["description"] is not None:
            updates["description"] = updates["description"].strip() or None

        try:
            with session.begin():
                role = self.repository.get_role(session, tenant_id, role_id)
                if role is None:
                    raise RoleNotFoundError("Role not found")
                if "name" in updates:
                    existing = self.repository.get_role_by_name(
                        session, tenant_id, updates["name"]
                    )
                    if existing is not None and existing.id != role.id:
                        raise RoleManagementError("A role with this name already exists")
                if updates.get("is_active") is False and self.repository.role_has_all_permission(
                    session, role.id
                ):
                    raise RoleManagementError(
                        "The system administrator role cannot be deactivated"
                    )
                for field, value in updates.items():
                    setattr(role, field, value)
                session.flush()
                return role
        except IntegrityError as error:
            raise RoleManagementError("Role could not be updated") from error

    def replace_permissions(
        self,
        session: Session,
        tenant_id: int,
        role_id: int,
        grants: list[RolePermissionGrantInput],
    ) -> None:
        codes = [grant.permission_code for grant in grants]
        if len(codes) != len(set(codes)):
            raise RoleManagementError("Each permission can be assigned only once")
        if ALL_PERMISSION in codes or "permissions.manage" in codes:
            raise RoleManagementError(
                "System administrator permissions cannot be assigned to custom roles"
            )
        if any(grant.scope not in SUPPORTED_SCOPES for grant in grants):
            raise RoleManagementError("Unsupported permission scope")
        allowed_scopes_by_permission = {
            "sell": {"assigned_stores", "all_tenant_stores"},
            "inventory.view": {"assigned_locations", "all_tenant_locations"},
            "inventory.manage": {"assigned_locations", "all_tenant_locations"},
        }
        for grant in grants:
            allowed = allowed_scopes_by_permission.get(
                grant.permission_code, {"assigned_stores"}
            )
            if grant.scope not in allowed:
                raise RoleManagementError(
                    f"Unsupported scope for {grant.permission_code}; allowed: {', '.join(sorted(allowed))}"
                )

        with session.begin():
            role = self.repository.get_role(session, tenant_id, role_id)
            if role is None:
                raise RoleNotFoundError("Role not found")
            if self.repository.role_has_all_permission(session, role.id):
                raise RoleManagementError(
                    "The system administrator role permissions cannot be changed"
                )

            permissions = {
                permission.code: permission
                for permission in self.repository.list_permissions(session)
            }
            unknown = sorted(set(codes) - set(permissions))
            if unknown:
                raise RoleManagementError(
                    "Unknown permission code(s): " + ", ".join(unknown)
                )

            session.execute(
                delete(RolePermission).where(RolePermission.role_id == role.id)
            )
            session.add_all(
                [
                    RolePermission(
                        role_id=role.id,
                        permission_id=permissions[grant.permission_code].id,
                        scope=grant.scope,
                    )
                    for grant in grants
                ]
            )
            session.flush()
