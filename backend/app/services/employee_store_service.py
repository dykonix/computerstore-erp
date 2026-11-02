from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.employee_store import EmployeeStore
from app.models.store import Store
from app.repositories.employee_store_repository import EmployeeStoreRepository
from app.schemas.employee_store import EmployeeStoreAssignmentCreate


class EmployeeStoreAssignmentError(Exception):
    pass


class EmployeeStoreService:
    """Legacy service name; assignments are user-to-store mappings."""

    def __init__(self, repository: EmployeeStoreRepository | None = None) -> None:
        self.repository = repository or EmployeeStoreRepository()

    def assign_store(self, session: Session, tenant_id: int, request: EmployeeStoreAssignmentCreate) -> EmployeeStore:
        try:
            with session.begin():
                user = self.repository.get_user(session, tenant_id, request.user_id)
                if user is None:
                    raise EmployeeStoreAssignmentError("User does not exist in the current tenant")
                if not user.is_active:
                    raise EmployeeStoreAssignmentError("Inactive users cannot receive store assignments")
                store = self.repository.get_store(session, tenant_id, request.store_id)
                if store is None:
                    raise EmployeeStoreAssignmentError("Store does not exist in the current tenant")
                if not store.is_active:
                    raise EmployeeStoreAssignmentError("Inactive stores cannot receive assignments")
                if self.repository.get_assignment(session, request.user_id, request.store_id) is not None:
                    raise EmployeeStoreAssignmentError("User is already assigned to this store")
                return self.repository.add_assignment(session, request.user_id, request.store_id)
        except IntegrityError as error:
            raise EmployeeStoreAssignmentError("User is already assigned to this store") from error

    def remove_store(self, session: Session, tenant_id: int, user_id: int, store_id: int) -> None:
        with session.begin():
            if self.repository.get_user(session, tenant_id, user_id) is None:
                raise EmployeeStoreAssignmentError("User does not exist in the current tenant")
            if self.repository.get_store(session, tenant_id, store_id) is None:
                raise EmployeeStoreAssignmentError("Store does not exist in the current tenant")
            assignment = self.repository.get_assignment(session, user_id, store_id)
            if assignment is None:
                raise EmployeeStoreAssignmentError("Store assignment not found")
            self.repository.remove_assignment(session, assignment)

    def list_stores(self, session: Session, tenant_id: int, user_id: int) -> list[Store]:
        if self.repository.get_user(session, tenant_id, user_id) is None:
            raise EmployeeStoreAssignmentError("User does not exist in the current tenant")
        return self.repository.list_stores_for_user(session, tenant_id, user_id)
