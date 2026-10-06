from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.auth import (
    AccessTokenResponse,
    AuthenticatedUserResponse,
    LoginRequest,
)
from app.security.jwt import JWTConfigurationError
from app.services.authorization_service import AuthorizationService
from app.services.auth_service import AuthService, InvalidCredentialsError

router = APIRouter(prefix="/auth", tags=["authentication"])


def _service() -> AuthService:
    return AuthService()


@router.post("/login", response_model=AccessTokenResponse)
def login(
    request: LoginRequest,
    session: Session = Depends(get_db),
    service: AuthService = Depends(_service),
) -> AccessTokenResponse:
    try:
        access_token = service.login(session, request)
        return AccessTokenResponse(access_token=access_token)
    except InvalidCredentialsError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error
    except JWTConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication is not configured",
        ) from error


@router.get("/me", response_model=AuthenticatedUserResponse)
def get_authenticated_user(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> AuthenticatedUserResponse:
    permissions = AuthorizationService().effective_permissions(session, current_user)
    return AuthenticatedUserResponse(
        id=current_user.id,
        email=current_user.email,
        employee_id=current_user.employee_id,
        permissions=permissions,
    )