import os
from collections.abc import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database.session import engine, get_db
from app.models.employee import Employee
from app.models.user import User
from app.security.jwt import InvalidAccessTokenError, JWTConfigurationError
from app.services.authorization_service import (
    AuthorizationService,
    PermissionDeniedError,
)
from app.services.auth_service import (
    AuthService,
    InvalidAuthenticatedEmployeeError,
)


_bearer_scheme = HTTPBearer(auto_error=False)


def get_auth_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


def get_current_tenant_id() -> int:
    """Temporary tenant context until authentication supplies the tenant."""
    value = os.getenv("CURRENT_TENANT_ID", "1")
    try:
        return int(value)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Current tenant context is invalid",
        ) from error


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    session: Session = Depends(get_auth_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return AuthService().get_user_from_access_token(
            session, credentials.credentials
        )
    except InvalidAccessTokenError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error
    except JWTConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication is not configured",
        ) from error


def get_current_tenant(current_user: User = Depends(get_current_user)) -> int:
    return current_user.tenant_id


def get_current_employee(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_auth_db),
) -> Employee:
    try:
        return AuthService().get_employee_for_user(session, current_user)
    except InvalidAuthenticatedEmployeeError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="An active employee profile is required",
        ) from error


def require_permission(permission_code: str):
    def permission_dependency(
        store_id: int | None = None,
        current_user: User = Depends(get_current_user),
        session: Session = Depends(get_auth_db),
    ) -> None:
        try:
            AuthorizationService().require_permission(
                session, current_user, permission_code, store_id
            )
        except PermissionDeniedError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied",
            ) from error

    permission_dependency.__name__ = f"require_{permission_code}_permission"
    return permission_dependency