from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest
from app.security.jwt import create_access_token, decode_access_token
from app.security.password import verify_dummy_password, verify_password
from app.services.user_service import UserIdentityError, UserIdentityService


class InvalidCredentialsError(Exception):
    pass


class InvalidAuthenticatedEmployeeError(Exception):
    pass


class AuthService:
    def __init__(self, repository: UserRepository | None = None) -> None:
        self.repository = repository or UserRepository()

    def login(self, session: Session, request: LoginRequest) -> str:
        try:
            email = UserIdentityService.normalize_email(request.email)
        except UserIdentityError:
            verify_dummy_password(request.password)
            raise InvalidCredentialsError("Invalid email or password") from None

        user = self.repository.get_by_email(session, email)
        if user is None:
            verify_dummy_password(request.password)
            raise InvalidCredentialsError("Invalid email or password")

        if not verify_password(request.password, user.password_hash) or not user.is_active:
            raise InvalidCredentialsError("Invalid email or password")

        try:
            employee = self.get_employee_for_user(session, user)
        except InvalidAuthenticatedEmployeeError:
            raise InvalidCredentialsError("Invalid email or password") from None
        if not employee.is_active:
            raise InvalidCredentialsError("Invalid email or password")

        return create_access_token(user.id)

    def get_user_from_access_token(self, session: Session, token: str) -> User:
        user_id = decode_access_token(token)
        user = self.repository.get_by_id(session, user_id)
        if user is None or not user.is_active:
            from app.security.jwt import InvalidAccessTokenError

            raise InvalidAccessTokenError("Invalid access token")
        return user

    def get_employee_for_user(self, session: Session, user: User) -> Employee:
        if user.employee_id is None:
            raise InvalidAuthenticatedEmployeeError("Employee profile is unavailable")
        employee = self.repository.get_employee(
            session, user.tenant_id, user.employee_id
        )
        if employee is None or not employee.is_active:
            raise InvalidAuthenticatedEmployeeError("Employee profile is unavailable")
        return employee