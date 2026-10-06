from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.supplier import Supplier


class SupplierRepository:
    def create(self, session: Session, supplier: Supplier) -> Supplier:
        session.add(supplier)
        session.flush()
        return supplier

    def get_by_id(
        self, session: Session, tenant_id: int, supplier_id: int
    ) -> Supplier | None:
        return session.scalar(
            select(Supplier).where(
                Supplier.tenant_id == tenant_id, Supplier.id == supplier_id
            )
        )

    def count_by_tenant(
        self, session: Session, tenant_id: int, is_active: bool | None = None
    ) -> int:
        statement = select(func.count()).select_from(Supplier).where(
            Supplier.tenant_id == tenant_id
        )
        if is_active is not None:
            statement = statement.where(Supplier.is_active.is_(is_active))
        return session.scalar(statement) or 0

    def list_by_tenant(
        self,
        session: Session,
        tenant_id: int,
        offset: int,
        limit: int,
        is_active: bool | None = None,
    ) -> list[Supplier]:
        statement = select(Supplier).where(Supplier.tenant_id == tenant_id)
        if is_active is not None:
            statement = statement.where(Supplier.is_active.is_(is_active))
        statement = statement.order_by(Supplier.id.desc()).offset(offset).limit(limit)
        return list(session.scalars(statement))

    def update(self, session: Session, supplier: Supplier) -> Supplier:
        session.flush()
        return supplier