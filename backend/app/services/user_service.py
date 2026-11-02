import re

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.role import Role
from app.models.user_role import UserRole
from app.models.user_store import UserStore
from app.models.user_godown import UserGodown
from app.models.godown import Godown
from app.models.store import Store
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserIdentityCreate, UserIdentityUpdate
from app.security.password import hash_password


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
                role_ids = list(dict.fromkeys(request.role_ids))
                if len(role_ids) != len(request.role_ids):
                    raise UserIdentityError("Each role can be selected only once")
                store_ids = list(dict.fromkeys(request.store_ids or []))
                if request.store_ids is not None and len(store_ids) != len(request.store_ids):
                    raise UserIdentityError("Each store can be selected only once")
                stores = []
                if store_ids:
                    stores = list(
                        session.scalars(
                            select(Store).where(
                                Store.tenant_id == tenant_id,
                                Store.id.in_(store_ids),
                                Store.is_active.is_(True),
                            )
                        )
                    )
                    if len(stores) != len(store_ids):
                        raise UserIdentityError(
                            "One or more selected stores are inactive or outside the current tenant"
                        )
                godown_ids = list(dict.fromkeys(request.godown_ids or []))
                if request.godown_ids is not None and len(godown_ids) != len(request.godown_ids):
                    raise UserIdentityError("Each godown can be selected only once")
                godowns = []
                if godown_ids:
                    godowns = list(session.scalars(
                        select(Godown).where(
                            Godown.tenant_id == tenant_id,
                            Godown.id.in_(godown_ids),
                            Godown.is_active.is_(True),
                        )
                    ))
                    if len(godowns) != len(godown_ids):
                        raise UserIdentityError(
                            "One or more selected godowns are inactive or outside the current tenant"
                        )
                roles = []
                if role_ids:
                    roles = list(
                        session.scalars(
                            select(Role).where(
                                Role.tenant_id == tenant_id,
                                Role.id.in_(role_ids),
                                Role.is_active.is_(True),
                            )
                        )
                    )
                    if len(roles) != len(role_ids):
                        raise UserIdentityError(
                            "One or more selected roles are inactive or outside the current tenant"
                        )
                user = self.repository.add_user(
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
                session.flush()
                for role in roles:
                    session.add(UserRole(user_id=user.id, role_id=role.id))
                if request.store_ids is not None:
                    session.execute(
                        delete(UserStore).where(
                            UserStore.user_id == user.id
                        )
                    )
                    for store in stores:
                        session.add(
                            UserStore(
                                user_id=user.id,
                                store_id=store.id,
                            )
                        )
                if request.godown_ids is not None:
                    session.execute(
                        delete(UserGodown).where(
                            UserGodown.user_id == user.id
                        )
                    )
                    for godown in godowns:
                        session.add(
                            UserGodown(
                                user_id=user.id,
                                godown_id=godown.id,
                            )
                        )
                session.flush()
                return user
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
        # Blank/omitted password means no password change. Never store plaintext.
        password = updates.pop("password", None)
        if password is not None and password.strip():
            if len(password) < 12:
                raise UserIdentityError("Password must be at least 12 characters")
            updates["password_hash"] = hash_password(password)
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