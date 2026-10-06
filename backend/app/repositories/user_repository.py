from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.user import User


class UserRepository:
    def get_by_email(self, session: Session, email: str) -> User | None:
        return session.scalar(select(User).where(User.email == email))

    def get_by_id(self, session: Session, user_id: int) -> User | None:
        return session.get(User, user_id)

    def get_employee(
        self, session: Session, tenant_id: int, employee_id: int
    ) -> Employee | None:
        return session.scalar(
            select(Employee).where(
                Employee.id == employee_id, Employee.tenant_id == tenant_id
            )
        )

    def get_user(
        self, session: Session, tenant_id: int, user_id: int
    ) -> User | None:
        return session.scalar(
            select(User).where(User.id == user_id, User.tenant_id == tenant_id)
        )

    def email_in_use(
        self, session: Session, email: str, exclude_user_id: int | None = None
    ) -> bool:
        statement = select(User.id).where(User.email == email)
        if exclude_user_id is not None:
            statement = statement.where(User.id != exclude_user_id)
        return session.scalar(statement) is not None

    def mobile_in_use(
        self, session: Session, mobile: str, exclude_user_id: int | None = None
    ) -> bool:
        statement = select(User.id).where(User.mobile == mobile)
        if exclude_user_id is not None:
            statement = statement.where(User.id != exclude_user_id)
        return session.scalar(statement) is not None

    def employee_in_use(
        self, session: Session, employee_id: int, exclude_user_id: int | None = None
    ) -> bool:
        statement = select(User.id).where(User.employee_id == employee_id)
        if exclude_user_id is not None:
            statement = statement.where(User.id != exclude_user_id)
        return session.scalar(statement) is not None

    def add_user(self, session: Session, user: User) -> User:
        session.add(user)
        session.flush()
        return user

    def update_user(self, session: Session, user: User) -> User:
        session.flush()
        return user