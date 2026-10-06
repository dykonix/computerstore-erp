from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.employee_store import EmployeeStore
from app.models.store import Store


class EmployeeStoreRepository:
    def get_employee(
        self, session: Session, tenant_id: int, employee_id: int
    ) -> Employee | None:
        return session.scalar(
            select(Employee).where(
                Employee.id == employee_id, Employee.tenant_id == tenant_id
            )
        )

    def get_store(
        self, session: Session, tenant_id: int, store_id: int
    ) -> Store | None:
        return session.scalar(
            select(Store).where(Store.id == store_id, Store.tenant_id == tenant_id)
        )

    def get_assignment(
        self, session: Session, employee_id: int, store_id: int
    ) -> EmployeeStore | None:
        return session.get(
            EmployeeStore,
            {"employee_id": employee_id, "store_id": store_id},
        )

    def add_assignment(
        self, session: Session, employee_id: int, store_id: int
    ) -> EmployeeStore:
        assignment = EmployeeStore(employee_id=employee_id, store_id=store_id)
        session.add(assignment)
        session.flush()
        return assignment

    def remove_assignment(self, session: Session, assignment: EmployeeStore) -> None:
        session.delete(assignment)
        session.flush()

    def list_stores_for_employee(
        self, session: Session, tenant_id: int, employee_id: int
    ) -> list[Store]:
        statement = (
            select(Store)
            .join(EmployeeStore, EmployeeStore.store_id == Store.id)
            .where(
                EmployeeStore.employee_id == employee_id,
                Store.tenant_id == tenant_id,
            )
            .order_by(Store.name, Store.id)
        )
        return list(session.scalars(statement))