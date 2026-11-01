from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_tenant, get_current_user, require_permission
from app.database.session import get_db
from app.models.employee import Employee
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.models.role_permission import RolePermission
from app.models.permission import Permission
from app.schemas.iam import (
    EmployeeOption,
    RoleOption,
    UserAdminCreate,
    UserAdminResponse,
    UserFormDataResponse,
    UserStatusUpdate,
)
from app.schemas.user import UserIdentityCreate, UserIdentityUpdate
from app.security.password import hash_password
from app.services.authorization_service import AuthorizationError, AuthorizationService
from app.services.user_service import (
    UserIdentityError,
    UserIdentityService,
    UserNotFoundError,
)

router = APIRouter(prefix="/users", tags=["identity and access management"])
_users_manage = Depends(require_permission("users.manage"))
_roles_manage = Depends(require_permission("roles.manage"))


def _user_response(session: Session, user: User) -> UserAdminResponse:
    employee = (
        session.scalar(
            select(Employee).where(
                Employee.id == user.employee_id,
                Employee.tenant_id == user.tenant_id,
            )
        )
        if user.employee_id is not None
        else None
    )
    role_rows = session.execute(
        select(Role.id, Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(
            UserRole.user_id == user.id,
            Role.tenant_id == user.tenant_id,
        )
        .order_by(Role.name)
    ).all()
    return UserAdminResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        mobile=user.mobile,
        employee_id=user.employee_id,
        employee_name=employee.name if employee else None,
        is_active=user.is_active,
        role_ids=[row.id for row in role_rows],
        role_names=[row.name for row in role_rows],
    )


@router.get("/form-data", response_model=UserFormDataResponse, dependencies=[_users_manage])
def get_user_form_data(
    tenant_id: int = Depends(get_current_tenant),
    session: Session = Depends(get_db),
) -> UserFormDataResponse:
    employees = session.scalars(
        select(Employee)
        .where(Employee.tenant_id == tenant_id)
        .order_by(Employee.name, Employee.email)
    )
    roles = session.scalars(
        select(Role)
        .where(Role.tenant_id == tenant_id)
        .order_by(Role.name)
    )
    return UserFormDataResponse(
        employees=[
            EmployeeOption(id=employee.id, name=employee.name, email=employee.email)
            for employee in employees
        ],
        roles=[RoleOption(id=role.id, name=role.name) for role in roles],
    )


@router.get("", response_model=list[UserAdminResponse], dependencies=[_users_manage])
def list_users(
    tenant_id: int = Depends(get_current_tenant),
    session: Session = Depends(get_db),
) -> list[UserAdminResponse]:
    users = session.scalars(
        select(User)
        .where(User.tenant_id == tenant_id)
        .order_by(User.username, User.id)
    )
    return [_user_response(session, user) for user in users]


@router.post("", response_model=UserAdminResponse, status_code=status.HTTP_201_CREATED, dependencies=[_users_manage])
def create_user(
    request: UserAdminCreate,
    tenant_id: int = Depends(get_current_tenant),
    session: Session = Depends(get_db),
) -> UserAdminResponse:
    try:
        user = UserIdentityService().create_user(
            session,
            tenant_id,
            UserIdentityCreate(
                username=request.username,
                email=request.email,
                mobile=request.mobile,
                employee_id=request.employee_id,
            ),
            hash_password(request.initial_password),
        )
        return _user_response(session, user)
    except UserIdentityError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.patch("/{user_id}", response_model=UserAdminResponse, dependencies=[_users_manage])
def update_user(
    user_id: int,
    request: UserIdentityUpdate,
    tenant_id: int = Depends(get_current_tenant),
    session: Session = Depends(get_db),
) -> UserAdminResponse:
    try:
        user = UserIdentityService().update_user(session, tenant_id, user_id, request)
        return _user_response(session, user)
    except UserNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found") from error
    except UserIdentityError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.patch("/{user_id}/status", response_model=UserAdminResponse, dependencies=[_users_manage])
def update_user_status(
    user_id: int,
    request: UserStatusUpdate,
    current_user: User = Depends(get_current_user),
    current_tenant_id: int = Depends(get_current_tenant),
    session: Session = Depends(get_db),
) -> UserAdminResponse:
    user = session.scalar(
        select(User).where(User.id == user_id, User.tenant_id == current_tenant_id)
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user_id == current_user.id and not request.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account",
        )
    user.is_active = request.is_active
    session.commit()
    session.refresh(user)
    return _user_response(session, user)


@router.post("/{user_id}/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[_roles_manage])
def assign_user_role(
    user_id: int,
    role_id: int,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant),
    session: Session = Depends(get_db),
) -> Response:
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own role assignments",
        )
    try:
        AuthorizationService().assign_role(session, tenant_id, user_id, role_id)
    except AuthorizationError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{user_id}/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[_roles_manage])
def remove_user_role(
    user_id: int,
    role_id: int,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant),
    session: Session = Depends(get_db),
) -> Response:
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own role assignments",
        )
    try:
        AuthorizationService().remove_role(session, tenant_id, user_id, role_id)
    except AuthorizationError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
