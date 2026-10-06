from sqlalchemy.orm import Session

from app.models.supplier import Supplier
from app.repositories.supplier_repository import SupplierRepository
from app.schemas.supplier import SupplierCreate, SupplierUpdate


class SupplierNotFoundError(Exception):
    pass


class SupplierValidationError(Exception):
    pass


class SupplierService:
    def __init__(self, repository: SupplierRepository | None = None) -> None:
        self.repository = repository or SupplierRepository()

    def create_supplier(
        self, session: Session, tenant_id: int, request: SupplierCreate
    ) -> Supplier:
        name = request.name.strip()
        if not name:
            raise SupplierValidationError("Supplier name is required")

        with session.begin():
            return self.repository.create(
                session,
                Supplier(
                    tenant_id=tenant_id,
                    name=name,
                    contact_person=request.contact_person,
                    phone=request.phone,
                    email=request.email,
                    address=request.address,
                    is_active=request.is_active,
                ),
            )

    def get_supplier(
        self, session: Session, tenant_id: int, supplier_id: int
    ) -> Supplier:
        supplier = self.repository.get_by_id(session, tenant_id, supplier_id)
        if supplier is None:
            raise SupplierNotFoundError("Supplier not found")
        return supplier

    def list_suppliers(
        self,
        session: Session,
        tenant_id: int,
        page: int,
        page_size: int,
        is_active: bool | None = None,
    ) -> tuple[list[Supplier], int]:
        total = self.repository.count_by_tenant(session, tenant_id, is_active)
        suppliers = self.repository.list_by_tenant(
            session,
            tenant_id,
            (page - 1) * page_size,
            page_size,
            is_active,
        )
        return suppliers, total

    def update_supplier(
        self,
        session: Session,
        tenant_id: int,
        supplier_id: int,
        request: SupplierUpdate,
    ) -> Supplier:
        updates = request.model_dump(exclude_unset=True)
        if not updates:
            raise SupplierValidationError("At least one field must be provided")
        if "name" in updates:
            name = updates["name"]
            if name is None or not name.strip():
                raise SupplierValidationError("Supplier name is required")
            updates["name"] = name.strip()
        if "is_active" in updates and updates["is_active"] is None:
            raise SupplierValidationError("is_active must be a boolean")

        with session.begin():
            supplier = self.repository.get_by_id(session, tenant_id, supplier_id)
            if supplier is None:
                raise SupplierNotFoundError("Supplier not found")
            for field, value in updates.items():
                setattr(supplier, field, value)
            return self.repository.update(session, supplier)