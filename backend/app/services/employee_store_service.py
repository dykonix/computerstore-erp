from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.employee_store import EmployeeStore
from app.models.store import Store
from app.repositories.employee_store_repository import EmployeeStoreRepository
from app.schemas.employee_store import EmployeeStoreAssignmentCreate


class EmployeeStoreAssignmentError(Exception):
    pass


class EmployeeStoreService:
    def __init__(
        self, repository: EmployeeStoreRepository | None = None
    ) -> None:
        self.repository = repository or EmployeeStoreRepository()

    def assign_store(
        self,
        session: Session,
        tenant_id: int,
        request: EmployeeStoreAssignmentCreate,
    ) -> EmployeeStore:
        try:
            with session.begin():
                employee = self.repository.get_employee(
                    session, tenant_id, request.employee_id
                )
                if employee is None:
                    raise EmployeeStoreAssignmentError(
                        "Employee does not exist in the current tenant"
                    )
                if not employee.is_active:
                    raise EmployeeStoreAssignmentError(
                        "Inactive employees cannot receive store assignments"
                    )

                store = self.repository.get_store(
                    session, tenant_id, request.store_id
                )
                if store is None:
                    raise EmployeeStoreAssignmentError(
                        "Store does not exist in the current tenant"
                    )
                if not store.is_active:
                    raise EmployeeStoreAssignmentError(
                        "Inactive stores cannot receive assignments"
                    )

                if self.repository.get_assignment(
                    session, request.employee_id, request.store_id
                ) is not None:
                    raise EmployeeStoreAssignmentError(
                        "Employee is already assigned to this store"
                    )
                return self.repository.add_assignment(
                    session, request.employee_id, request.store_id
                )
        except IntegrityError as error:
            raise EmployeeStoreAssignmentError(
                "Employee is already assigned to this store"
            ) from error

    def remove_store(
        self,
        session: Session,
        tenant_id: int,
        employee_id: int,
        store_id: int,
    ) -> None:
        with session.begin():
            employee = self.repository.get_employee(session, tenant_id, employee_id)
            if employee is None:
                raise EmployeeStoreAssignmentError(
                    "Employee does not exist in the current tenant"
                )
            store = self.repository.get_store(session, tenant_id, store_id)
            if store is None:
                raise EmployeeStoreAssignmentError(
                    "Store does not exist in the current tenant"
                )
            assignment = self.repository.get_assignment(session, employee_id, store_id)
            if assignment is None:
                raise EmployeeStoreAssignmentError("Store assignment not found")
            self.repository.remove_assignment(session, assignment)

    def list_stores(
        self, session: Session, tenant_id: int, employee_id: int
    ) -> list[Store]:
        employee = self.repository.get_employee(session, tenant_id, employee_id)
        if employee is None:
            raise EmployeeStoreAssignmentError(
                "Employee does not exist in the current tenant"
            )
        return self.repository.list_stores_for_employee(
            session, tenant_id, employee_id
        )