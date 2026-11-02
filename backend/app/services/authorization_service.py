from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.role_permission import RolePermission
from app.models.user import User
from app.models.user_role import UserRole
from app.repositories.authorization_repository import AuthorizationRepository


ASSIGNED_STORES = "assigned_stores"
ALL_TENANT_STORES = "all_tenant_stores"
ASSIGNED_LOCATIONS = "assigned_locations"
ALL_TENANT_LOCATIONS = "all_tenant_locations"
ALL_PERMISSION = "ALL"
SUPPORTED_SCOPES = {
    ASSIGNED_STORES,
    ALL_TENANT_STORES,
    ASSIGNED_LOCATIONS,
    ALL_TENANT_LOCATIONS,
}


class AuthorizationError(Exception):
    pass


class PermissionDeniedError(AuthorizationError):
    pass


class AuthorizationService:
    def __init__(
        self,
        repository: AuthorizationRepository | None = None,
    ) -> None:
        self.repository = repository or AuthorizationRepository()

    def is_super_admin(self, session: Session, user: User) -> bool:
        if not user.is_active:
            return False
        return any(
            code == ALL_PERMISSION
            for code, _scope in self.repository.list_active_user_permission_grants(
                session, user
            )
        )

    def effective_permissions(
        self,
        session: Session,
        user: User,
    ) -> list[str]:
        if not user.is_active:
            raise PermissionDeniedError("User is inactive")

        grants = self.repository.list_active_user_permission_grants(
            session,
            user,
        )

        grant_codes = {
            code
            for code, _scope in grants
        }

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
        godown_id: int | None = None,
    ) -> None:
        if not user.is_active:
            raise PermissionDeniedError("User is inactive")

        grants = self.repository.list_active_user_permission_grants(
            session,
            user,
        )

        registered_codes = set(
            self.repository.list_permission_codes(session)
        )

        if (
            permission_code not in registered_codes
            or permission_code == ALL_PERMISSION
        ):
            raise PermissionDeniedError("Permission denied")

        if store_id is not None and godown_id is not None:
            raise PermissionDeniedError("Exactly one inventory location must be supplied")
        if any(
            code == ALL_PERMISSION
            for code, _scope in grants
        ):
            if store_id is not None:
                self._validate_active_tenant_store(session, user.tenant_id, store_id)
            if godown_id is not None:
                self._validate_active_tenant_godown(session, user.tenant_id, godown_id)
            return

        matching_scopes = [
            scope
            for code, scope in grants
            if code == permission_code
        ]

        if not matching_scopes:
            raise PermissionDeniedError("Permission denied")

        if store_id is None and godown_id is None:
            return

        if store_id is not None:
            self._validate_active_tenant_store(session, user.tenant_id, store_id)
            if ALL_TENANT_STORES in matching_scopes or ALL_TENANT_LOCATIONS in matching_scopes:
                return
            if (ASSIGNED_STORES in matching_scopes or ASSIGNED_LOCATIONS in matching_scopes) and self.repository.user_has_store(session, user.id, store_id):
                return
        else:
            self._validate_active_tenant_godown(session, user.tenant_id, godown_id)
            if ALL_TENANT_LOCATIONS in matching_scopes:
                return
            if ASSIGNED_LOCATIONS in matching_scopes and self.repository.user_has_godown(session, user.id, godown_id):
                return
        raise PermissionDeniedError("Permission denied")

    def list_allowed_stores(
        self,
        session: Session,
        user: User,
        permission_code: str = "sell",
    ):
        if not user.is_active:
            raise PermissionDeniedError("User is inactive")

        grants = self.repository.list_active_user_permission_grants(
            session,
            user,
        )

        registered_codes = set(
            self.repository.list_permission_codes(session)
        )

        if (
            permission_code not in registered_codes
            or permission_code == ALL_PERMISSION
        ):
            raise PermissionDeniedError("Permission denied")

        if any(
            code == ALL_PERMISSION
            for code, _scope in grants
        ):
            return self.repository.list_active_tenant_stores(
                session,
                user.tenant_id,
            )

        matching_scopes = [
            scope
            for code, scope in grants
            if code == permission_code
        ]

        if not matching_scopes:
            raise PermissionDeniedError("Permission denied")

        if ALL_TENANT_STORES in matching_scopes or ALL_TENANT_LOCATIONS in matching_scopes:
            return self.repository.list_active_tenant_stores(
                session,
                user.tenant_id,
            )

        if ASSIGNED_STORES in matching_scopes or ASSIGNED_LOCATIONS in matching_scopes:
            return self.repository.list_user_stores(
                session,
                user.tenant_id,
                user.id,
            )

        raise PermissionDeniedError("Permission denied")

    def list_allowed_godowns(
        self, session: Session, user: User, permission_code: str = "inventory.view"
    ):
        if not user.is_active:
            raise PermissionDeniedError("User is inactive")
        grants = self.repository.list_active_user_permission_grants(session, user)
        registered = set(self.repository.list_permission_codes(session))
        if permission_code not in registered or permission_code == ALL_PERMISSION:
            raise PermissionDeniedError("Permission denied")
        scopes = [scope for code, scope in grants if code == ALL_PERMISSION or code == permission_code]
        if ALL_PERMISSION in {code for code, _scope in grants} or ALL_TENANT_LOCATIONS in scopes:
            return self.repository.list_active_tenant_godowns(session, user.tenant_id)
        if ASSIGNED_LOCATIONS not in scopes:
            return []
        return self.repository.list_user_godowns(session, user.tenant_id, user.id)

    def assign_role(
        self,
        session: Session,
        tenant_id: int,
        user_id: int,
        role_id: int,
    ) -> UserRole:
        try:
            with session.begin():
                user = self.repository.get_user(
                    session,
                    user_id,
                )

                if (
                    user is None
                    or user.tenant_id != tenant_id
                ):
                    raise AuthorizationError(
                        "User does not exist in the current tenant"
                    )

                role = self.repository.get_role(
                    session,
                    tenant_id,
                    role_id,
                )

                if role is None:
                    raise AuthorizationError(
                        "Role does not exist in the current tenant"
                    )

                if not user.is_active:
                    raise AuthorizationError(
                        "Inactive users cannot receive roles"
                    )

                if not role.is_active:
                    raise AuthorizationError(
                        "Inactive roles cannot be assigned"
                    )

                existing = self.repository.get_user_role(
                    session,
                    user_id,
                    role_id,
                )

                if existing is not None:
                    return existing

                return self.repository.add_user_role(
                    session,
                    user_id,
                    role_id,
                )

        except IntegrityError as error:
            raise AuthorizationError(
                "Role assignment could not be created"
            ) from error

    def remove_role(
        self,
        session: Session,
        tenant_id: int,
        user_id: int,
        role_id: int,
    ) -> None:
        with session.begin():
            user = self.repository.get_user(
                session,
                user_id,
            )

            if (
                user is None
                or user.tenant_id != tenant_id
            ):
                raise AuthorizationError(
                    "User does not exist in the current tenant"
                )

            role = self.repository.get_role(
                session,
                tenant_id,
                role_id,
            )

            if role is None:
                raise AuthorizationError(
                    "Role does not exist in the current tenant"
                )

            assignment = self.repository.get_user_role(
                session,
                user_id,
                role_id,
            )

            if assignment is not None:
                self.repository.remove_user_role(
                    session,
                    assignment,
                )

    def grant_permission(
        self,
        session: Session,
        tenant_id: int,
        role_id: int,
        permission_code: str,
        scope: str = ASSIGNED_STORES,
    ) -> RolePermission:
        if scope not in SUPPORTED_SCOPES:
            raise AuthorizationError(
                "Unsupported permission scope"
            )

        try:
            with session.begin():
                role = self.repository.get_role(
                    session,
                    tenant_id,
                    role_id,
                )

                if role is None:
                    raise AuthorizationError(
                        "Role does not exist in the current tenant"
                    )

                permission = self.repository.get_permission(
                    session,
                    permission_code,
                )

                if permission is None:
                    raise AuthorizationError(
                        "Permission does not exist"
                    )

                grant = self.repository.get_role_permission(
                    session,
                    role_id,
                    permission.id,
                )

                if grant is not None:
                    grant.scope = scope
                    session.flush()
                    return grant

                return self.repository.add_role_permission(
                    session,
                    role_id,
                    permission.id,
                    scope,
                )

        except IntegrityError as error:
            raise AuthorizationError(
                "Permission grant could not be created"
            ) from error

    def _validate_active_tenant_store(
        self,
        session: Session,
        tenant_id: int,
        store_id: int,
    ) -> None:
        store = self.repository.get_store(
            session,
            tenant_id,
            store_id,
        )

        if store is None or not store.is_active:
            raise PermissionDeniedError(
                "Permission denied"
            )

    def _validate_active_tenant_godown(
        self, session: Session, tenant_id: int, godown_id: int
    ) -> None:
        godown = self.repository.get_godown(session, tenant_id, godown_id)
        if godown is None or not godown.is_active:
            raise PermissionDeniedError("Permission denied")
