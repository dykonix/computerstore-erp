from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_tenant, get_current_user, get_auth_db, require_permission
from app.database.session import get_db
from app.models.employee import Employee
from app.models.employee_store import EmployeeStore
from app.models.employee_godown import EmployeeGodown
from app.models.godown import Godown
from app.models.store import Store
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.repositories.authorization_repository import AuthorizationRepository
from app.repositories.role_repository import RoleRepository
from app.schemas.iam import (
    EmployeeOption,
    RoleOption,
    StoreOption,
    GodownOption,
    UserAdminCreate,
    UserAdminResponse,
    UserFormDataResponse,
    UserStatusUpdate,
)
from app.schemas.user import UserIdentityCreate, UserIdentityUpdate
from app.security.password import hash_password
from app.services.authorization_service import AuthorizationError, AuthorizationService, PermissionDeniedError
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
        .where(Employee.tenant_id == tenant_id, Employee.is_active.is_(True))
        .order_by(Employee.name, Employee.email)
    )
    roles = session.scalars(
        select(Role)
        .where(Role.tenant_id == tenant_id, Role.is_active.is_(True))
        .order_by(Role.name)
    )
    stores = list(
        session.scalars(
            select(Store)
            .where(Store.tenant_id == tenant_id, Store.is_active.is_(True))
            .order_by(Store.name)
        )
    )
    godowns = list(session.scalars(
        select(Godown).where(Godown.tenant_id == tenant_id, Godown.is_active.is_(True)).order_by(Godown.name)
    ))
    employee_godown_rows = session.execute(
        select(EmployeeGodown.employee_id, EmployeeGodown.godown_id)
        .join(Godown, Godown.id == EmployeeGodown.godown_id)
        .where(Godown.tenant_id == tenant_id, Godown.is_active.is_(True))
    ).all()
    employee_ids_by_godown: dict[int, list[int]] = {godown.id: [] for godown in godowns}
    for employee_id, godown_id in employee_godown_rows:
        employee_ids_by_godown.setdefault(godown_id, []).append(employee_id)
    employee_store_rows = session.execute(
        select(EmployeeStore.employee_id, EmployeeStore.store_id)
        .join(Store, Store.id == EmployeeStore.store_id)
        .where(Store.tenant_id == tenant_id, Store.is_active.is_(True))
    ).all()
    employee_ids_by_store: dict[int, list[int]] = {store.id: [] for store in stores}
    for employee_id, store_id in employee_store_rows:
        employee_ids_by_store.setdefault(store_id, []).append(employee_id)
    return UserFormDataResponse(
        employees=[
            EmployeeOption(id=employee.id, name=employee.name, email=employee.email)
            for employee in employees
        ],
        roles=[RoleOption(id=role.id, name=role.name) for role in roles],
        stores=[
            StoreOption(id=store.id, name=store.name, employee_ids=employee_ids_by_store.get(store.id, []))
            for store in stores
        ],
        godowns=[
            GodownOption(id=godown.id, name=godown.name, employee_ids=employee_ids_by_godown.get(godown.id, []))
            for godown in godowns
        ],
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
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant),
    auth_session: Session = Depends(get_auth_db),
    session: Session = Depends(get_db),
) -> UserAdminResponse:
    if request.role_ids:
        try:
            AuthorizationService().require_permission(
                auth_session, current_user, "roles.manage"
            )
        except PermissionDeniedError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Role assignment requires roles.manage permission",
            ) from error
        role_repository = RoleRepository()
        for role_id in set(request.role_ids):
            if role_repository.role_has_all_permission(auth_session, role_id) and not AuthorizationService().is_super_admin(auth_session, current_user):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only a system administrator can assign the system administrator role",
                )
    if request.store_ids is not None or request.godown_ids is not None:
        try:
            AuthorizationService().require_permission(
                auth_session, current_user, "employees.manage"
            )
        except PermissionDeniedError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Store assignment requires employees.manage permission",
            ) from error
    try:
        user = UserIdentityService().create_user(
            session,
            tenant_id,
            UserIdentityCreate(
                username=request.username,
                email=request.email,
                mobile=request.mobile,
                employee_id=request.employee_id,
                role_ids=request.role_ids,
                store_ids=request.store_ids,
                godown_ids=request.godown_ids,
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
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant),
    auth_session: Session = Depends(get_auth_db),
    session: Session = Depends(get_db),
) -> UserAdminResponse:
    target_user = AuthorizationRepository().get_user(auth_session, user_id)
    if target_user is None or target_user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    authorization = AuthorizationService()
    if (
        authorization.is_super_admin(auth_session, target_user)
        and not authorization.is_super_admin(auth_session, current_user)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a system administrator can edit a system administrator account",
        )
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
    auth_session: Session = Depends(get_auth_db),
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
    authorization = AuthorizationService()
    target_is_super_admin = authorization.is_super_admin(auth_session, user)
    actor_is_super_admin = authorization.is_super_admin(auth_session, current_user)
    if target_is_super_admin and not actor_is_super_admin and not request.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a system administrator can deactivate a system administrator",
        )
    if (
        target_is_super_admin
        and not request.is_active
        and AuthorizationRepository().count_active_super_admins(
            auth_session, current_tenant_id
        ) <= 1
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The last active system administrator cannot be deactivated",
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
    auth_session: Session = Depends(get_auth_db),
    session: Session = Depends(get_db),
) -> Response:
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own role assignments",
        )
    target_user = AuthorizationRepository().get_user(auth_session, user_id)
    target_role = RoleRepository().get_role(auth_session, tenant_id, role_id)
    if target_user is None or target_user.tenant_id != tenant_id or target_role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User or role not found")
    authorization = AuthorizationService()
    if (
        not authorization.is_super_admin(auth_session, current_user)
        and RoleRepository().role_has_all_permission(auth_session, role_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a system administrator can assign the system administrator role",
        )
    try:
        authorization.assign_role(session, tenant_id, user_id, role_id)
    except AuthorizationError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{user_id}/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[_roles_manage])
def remove_user_role(
    user_id: int,
    role_id: int,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant),
    auth_session: Session = Depends(get_auth_db),
    session: Session = Depends(get_db),
) -> Response:
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own role assignments",
        )
    target_user = AuthorizationRepository().get_user(auth_session, user_id)
    target_role = RoleRepository().get_role(auth_session, tenant_id, role_id)
    if target_user is None or target_user.tenant_id != tenant_id or target_role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User or role not found")
    role_repository = RoleRepository()
    if (
        role_repository.user_has_role(auth_session, user_id, role_id)
        and role_repository.role_has_all_permission(auth_session, role_id)
    ):
        authorization = AuthorizationService()
        if not authorization.is_super_admin(auth_session, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only a system administrator can remove the system administrator role",
            )
        if (
            target_user.is_active
            and AuthorizationRepository().count_active_super_admins(
                auth_session, tenant_id
            ) <= 1
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The last active system administrator role cannot be removed",
            )
    try:
        AuthorizationService().remove_role(session, tenant_id, user_id, role_id)
    except AuthorizationError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
