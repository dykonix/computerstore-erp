from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.employee_store import EmployeeStore
from app.models.store import Store
from app.models.user import User


class EmployeeStoreRepository:
    """Compatibility service name; assignments are keyed by user_id."""

    def get_user(self, session: Session, tenant_id: int, user_id: int) -> User | None:
        return session.scalar(
            select(User).where(User.id == user_id, User.tenant_id == tenant_id)
        )

    def get_store(self, session: Session, tenant_id: int, store_id: int) -> Store | None:
        return session.scalar(
            select(Store).where(Store.id == store_id, Store.tenant_id == tenant_id)
        )

    def get_assignment(self, session: Session, user_id: int, store_id: int) -> EmployeeStore | None:
        return session.get(EmployeeStore, {"user_id": user_id, "store_id": store_id})

    def add_assignment(self, session: Session, user_id: int, store_id: int) -> EmployeeStore:
        assignment = EmployeeStore(user_id=user_id, store_id=store_id)
        session.add(assignment)
        session.flush()
        return assignment

    def remove_assignment(self, session: Session, assignment: EmployeeStore) -> None:
        session.delete(assignment)
        session.flush()

    def list_stores_for_user(self, session: Session, tenant_id: int, user_id: int) -> list[Store]:
        statement = (
            select(Store)
            .join(EmployeeStore, EmployeeStore.store_id == Store.id)
            .where(EmployeeStore.user_id == user_id, Store.tenant_id == tenant_id)
            .order_by(Store.name, Store.id)
        )
        return list(session.scalars(statement))
