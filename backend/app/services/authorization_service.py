from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.role_permission import RolePermission
from app.models.user import User
from app.models.user_role import UserRole
from app.repositories.authorization_repository import AuthorizationRepository


ASSIGNED_STORES = "assigned_stores"
ALL_TENANT_STORES = "all_tenant_stores"
ALL_PERMISSION = "ALL"
SUPPORTED_SCOPES = {ASSIGNED_STORES, ALL_TENANT_STORES}


class AuthorizationError(Exception):
    pass


class PermissionDeniedError(AuthorizationError):
    pass


class AuthorizationService:
    def __init__(self, repository: AuthorizationRepository | None = None) -> None:
        self.repository = repository or AuthorizationRepository()

    def effective_permissions(self, session: Session, user: User) -> list[str]:
        if not user.is_active:
            raise PermissionDeniedError("User is inactive")
        grants = self.repository.list_active_user_permission_grants(session, user)
        grant_codes = {code for code, _scope in grants}
        if ALL_PERMISSION in grant_codes:
            return [
                code
                for code in self.repository.list_permission_codes(session)
                if code != ALL_PERMISSION
            ]
        return sorted(grant_codes)

    def require_permission(
        self,
        session: Session,
        user: User,
        permission_code: str,
        store_id: int | None = None,
    ) -> None:
        if not user.is_active:
            raise PermissionDeniedError("User is inactive")
        grants = self.repository.list_active_user_permission_grants(session, user)
        registered_codes = set(self.repository.list_permission_codes(session))
        if permission_code not in registered_codes or permission_code == ALL_PERMISSION:
            raise PermissionDeniedError("Permission denied")
        if store_id is not None:
            self._get_active_employee(session, user)
        if any(code == ALL_PERMISSION for code, _scope in grants):
            if store_id is not None:
                self._validate_active_tenant_store(session, user.tenant_id, store_id)
            return

        matching_scopes = [
            scope for code, scope in grants if code == permission_code
        ]
        if not matching_scopes:
            raise PermissionDeniedError("Permission denied")
        if store_id is None:
            return

        self._validate_active_tenant_store(session, user.tenant_id, store_id)
        if ALL_TENANT_STORES in matching_scopes:
            return
        if ASSIGNED_STORES not in matching_scopes:
            raise PermissionDeniedError("Permission denied")

        employee = self._get_active_employee(session, user)
        if not self.repository.employee_has_store(session, employee.id, store_id):
            raise PermissionDeniedError("Permission denied")

    def assign_role(
        self, session: Session, tenant_id: int, user_id: int, role_id: int
    ) -> UserRole:
        try:
            with session.begin():
                user = self.repository.get_user(session, user_id)
                if user is None or user.tenant_id != tenant_id:
                    raise AuthorizationError("User does not exist in the current tenant")
                role = self.repository.get_role(session, tenant_id, role_id)
                if role is None:
                    raise AuthorizationError("Role does not exist in the current tenant")
                if not user.is_active:
                    raise AuthorizationError("Inactive users cannot receive roles")
                if not role.is_active:
                    raise AuthorizationError("Inactive roles cannot be assigned")
                if self.repository.get_user_role(session, user_id, role_id) is not None:
                    return self.repository.get_user_role(session, user_id, role_id)
                return self.repository.add_user_role(session, user_id, role_id)
        except IntegrityError as error:
            raise AuthorizationError("Role assignment could not be created") from error

    def remove_role(
        self, session: Session, tenant_id: int, user_id: int, role_id: int
    ) -> None:
        with session.begin():
            user = self.repository.get_user(session, user_id)
            if user is None or user.tenant_id != tenant_id:
                raise AuthorizationError("User does not exist in the current tenant")
            role = self.repository.get_role(session, tenant_id, role_id)
            if role is None:
                raise AuthorizationError("Role does not exist in the current tenant")
            assignment = self.repository.get_user_role(session, user_id, role_id)
            if assignment is not None:
                self.repository.remove_user_role(session, assignment)

    def grant_permission(
        self,
        session: Session,
        tenant_id: int,
        role_id: int,
        permission_code: str,
        scope: str = ASSIGNED_STORES,
    ) -> RolePermission:
        if scope not in SUPPORTED_SCOPES:
            raise AuthorizationError("Unsupported permission scope")
        try:
            with session.begin():
                role = self.repository.get_role(session, tenant_id, role_id)
                if role is None:
                    raise AuthorizationError("Role does not exist in the current tenant")
                permission = self.repository.get_permission(session, permission_code)
                if permission is None:
                    raise AuthorizationError("Permission does not exist")
                grant = self.repository.get_role_permission(
                    session, role_id, permission.id
                )
                if grant is not None:
                    grant.scope = scope
                    session.flush()
                    return grant
                return self.repository.add_role_permission(
                    session, role_id, permission.id, scope
                )
        except IntegrityError as error:
            raise AuthorizationError("Permission grant could not be created") from error

    def _validate_active_tenant_store(
        self, session: Session, tenant_id: int, store_id: int
    ) -> None:
        store = self.repository.get_store(session, tenant_id, store_id)
        if store is None or not store.is_active:
            raise PermissionDeniedError("Permission denied")

    def _get_active_employee(self, session: Session, user: User):
        if user.employee_id is None:
            raise PermissionDeniedError("Permission denied")
        employee = self.repository.get_employee(
            session, user.tenant_id, user.employee_id
        )
        if employee is None or not employee.is_active:
            raise PermissionDeniedError("Permission denied")
        return employee