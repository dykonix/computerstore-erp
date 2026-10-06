import re

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserIdentityCreate, UserIdentityUpdate


_EMAIL_PATTERN = re.compile(
    r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~.-]+@"
    r"(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+"
    r"[A-Za-z]{2,63}"
)
_MOBILE_PATTERN = re.compile(r"\+?\d{7,15}")
_MOBILE_SEPARATORS = re.compile(r"[\s().-]+")


class UserIdentityError(Exception):
    pass


class UserNotFoundError(Exception):
    pass


class UserIdentityService:
    def __init__(self, repository: UserRepository | None = None) -> None:
        self.repository = repository or UserRepository()

    @staticmethod
    def normalize_email(value: str) -> str:
        canonical = value.strip().lower()
        local_part = canonical.partition("@")[0]
        if (
            not canonical
            or local_part.startswith(".")
            or local_part.endswith(".")
            or ".." in local_part
            or _EMAIL_PATTERN.fullmatch(canonical) is None
        ):
            raise UserIdentityError("A valid email address is required")
        return canonical

    @staticmethod
    def normalize_mobile(value: str) -> str:
        canonical = _MOBILE_SEPARATORS.sub("", value.strip())
        if not canonical or _MOBILE_PATTERN.fullmatch(canonical) is None:
            raise UserIdentityError("A valid mobile number is required")
        return canonical

    def create_user(
        self,
        session: Session,
        tenant_id: int,
        request: UserIdentityCreate,
        password_hash: str,
    ) -> User:
        username = request.username.strip()
        if not username:
            raise UserIdentityError("Username is required")
        if not password_hash:
            raise UserIdentityError("A password hash is required")

        email = self.normalize_email(request.email)
        mobile = self.normalize_mobile(request.mobile)

        try:
            with session.begin():
                self._validate_identity(
                    session, tenant_id, email, mobile, request.employee_id
                )
                return self.repository.add_user(
                    session,
                    User(
                        tenant_id=tenant_id,
                        username=username,
                        password_hash=password_hash,
                        email=email,
                        mobile=mobile,
                        employee_id=request.employee_id,
                    ),
                )
        except IntegrityError as error:
            raise UserIdentityError(
                "Email, mobile, or employee is already assigned to a user"
            ) from error

    def update_user(
        self,
        session: Session,
        tenant_id: int,
        user_id: int,
        request: UserIdentityUpdate,
    ) -> User:
        updates = request.model_dump(exclude_unset=True)
        if not updates:
            raise UserIdentityError("At least one identity field must be provided")
        if "email" in updates:
            if updates["email"] is None:
                raise UserIdentityError("Email cannot be empty")
            updates["email"] = self.normalize_email(updates["email"])
        if "mobile" in updates:
            if updates["mobile"] is None:
                raise UserIdentityError("Mobile cannot be empty")
            updates["mobile"] = self.normalize_mobile(updates["mobile"])

        try:
            with session.begin():
                user = self.repository.get_user(session, tenant_id, user_id)
                if user is None:
                    raise UserNotFoundError("User not found")
                employee_id = updates.get("employee_id", user.employee_id)
                self._validate_employee(session, tenant_id, employee_id)
                if employee_id is not None and self.repository.employee_in_use(
                    session, employee_id, exclude_user_id=user.id
                ):
                    raise UserIdentityError(
                        "Employee is already associated with another user"
                    )

                if "email" in updates and self.repository.email_in_use(
                    session, updates["email"], exclude_user_id=user.id
                ):
                    raise UserIdentityError("Email is already in use")
                if "mobile" in updates and self.repository.mobile_in_use(
                    session, updates["mobile"], exclude_user_id=user.id
                ):
                    raise UserIdentityError("Mobile number is already in use")

                for field, value in updates.items():
                    setattr(user, field, value)
                return self.repository.update_user(session, user)
        except IntegrityError as error:
            raise UserIdentityError(
                "Email, mobile, or employee is already assigned to a user"
            ) from error

    def _validate_identity(
        self,
        session: Session,
        tenant_id: int,
        email: str,
        mobile: str,
        employee_id: int | None,
    ) -> None:
        if self.repository.email_in_use(session, email):
            raise UserIdentityError("Email is already in use")
        if self.repository.mobile_in_use(session, mobile):
            raise UserIdentityError("Mobile number is already in use")
        self._validate_employee(session, tenant_id, employee_id)
        if employee_id is not None and self.repository.employee_in_use(
            session, employee_id
        ):
            raise UserIdentityError("Employee is already associated with another user")

    def _validate_employee(
        self, session: Session, tenant_id: int, employee_id: int | None
    ) -> None:
        if employee_id is not None and self.repository.get_employee(
            session, tenant_id, employee_id
        ) is None:
            raise UserIdentityError("Employee does not exist in the current tenant")