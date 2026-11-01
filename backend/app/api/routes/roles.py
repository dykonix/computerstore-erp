from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_auth_db, get_current_tenant, get_current_user, require_permission
from app.database.session import get_db
from app.models.user import User
from app.repositories.role_repository import RoleRepository
from app.schemas.role import (
    PermissionOption,
    RoleCreate,
    RoleFormDataResponse,
    RolePermissionReplaceRequest,
    RolePermissionResponse,
    RoleResponse,
    RoleUpdate,
)
from app.services.authorization_service import AuthorizationService
from app.services.role_management_service import (
    RoleManagementError,
    RoleManagementService,
    RoleNotFoundError,
)

router = APIRouter(prefix="/roles", tags=["identity and access management"])
_roles_manage = Depends(require_permission("roles.manage"))
_permissions_manage = Depends(require_permission("permissions.manage"))


def _role_response(session: Session, role) -> RoleResponse:
    grants = RoleRepository().list_role_permissions(session, role.id)
    return RoleResponse(
        id=role.id,
        name=role.name,
        description=role.description,
        is_active=role.is_active,
        permissions=[
            RolePermissionResponse(
                permission_code=code,
                description=description,
                scope=scope,
            )
            for code, description, scope in grants
        ],
    )


@router.get("/form-data", response_model=RoleFormDataResponse, dependencies=[_roles_manage])
def get_role_form_data(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> RoleFormDataResponse:
    repository = RoleRepository()
    return RoleFormDataResponse(
        permissions=[
            PermissionOption(code=permission.code, description=permission.description)
            for permission in repository.list_permissions(session)
        ],
        can_manage_permissions=AuthorizationService().is_super_admin(session, current_user),
    )


@router.get("", response_model=list[RoleResponse], dependencies=[_roles_manage])
def list_roles(
    tenant_id: int = Depends(get_current_tenant),
    session: Session = Depends(get_db),
) -> list[RoleResponse]:
    repository = RoleRepository()
    return [
        _role_response(session, role)
        for role in repository.list_roles(session, tenant_id)
    ]


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED, dependencies=[_roles_manage])
def create_role(
    request: RoleCreate,
    tenant_id: int = Depends(get_current_tenant),
    session: Session = Depends(get_db),
) -> RoleResponse:
    try:
        role = RoleManagementService().create_role(session, tenant_id, request)
        return _role_response(session, role)
    except RoleManagementError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.patch("/{role_id}", response_model=RoleResponse, dependencies=[_roles_manage])
def update_role(
    role_id: int,
    request: RoleUpdate,
    tenant_id: int = Depends(get_current_tenant),
    session: Session = Depends(get_db),
) -> RoleResponse:
    try:
        role = RoleManagementService().update_role(session, tenant_id, role_id, request)
        return _role_response(session, role)
    except RoleNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found") from error
    except RoleManagementError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.put("/{role_id}/permissions", response_model=RoleResponse, dependencies=[_roles_manage, _permissions_manage])
def replace_role_permissions(
    role_id: int,
    request: RolePermissionReplaceRequest,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant),
    auth_session: Session = Depends(get_auth_db),
    session: Session = Depends(get_db),
) -> RoleResponse:
    if not AuthorizationService().is_super_admin(auth_session, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a system administrator can change role permissions",
        )
    service = RoleManagementService()
    try:
        service.replace_permissions(session, tenant_id, role_id, request.permissions)
        role = RoleRepository().get_role(session, tenant_id, role_id)
        if role is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        return _role_response(session, role)
    except RoleNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found") from error
    except RoleManagementError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
