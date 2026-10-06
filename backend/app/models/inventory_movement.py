from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"
    __table_args__ = (
        CheckConstraint(
            "quantity > 0", name="ck_inventory_movements_quantity_positive"
        ),
        CheckConstraint(
            "movement_type IN ('OPENING', 'TRANSFER', 'SALE', 'ADJUSTMENT', 'RESERVATION', 'RELEASE')",
            name="ck_inventory_movements_movement_type",
        ),
        Index("ix_inventory_movements_tenant_id", "tenant_id"),
        Index("ix_inventory_movements_product_id", "product_id"),
        Index("ix_inventory_movements_created_at", "created_at"),
        Index("ix_inventory_movements_movement_type", "movement_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"), nullable=False
    )
    supplier_id: Mapped[int | None] = mapped_column(
        ForeignKey("suppliers.id"), nullable=True
    )
    movement_type: Mapped[str] = mapped_column(String, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    from_store_id: Mapped[int | None] = mapped_column(
        ForeignKey("stores.id"), nullable=True
    )
    from_godown_id: Mapped[int | None] = mapped_column(
        ForeignKey("godowns.id"), nullable=True
    )
    to_store_id: Mapped[int | None] = mapped_column(
        ForeignKey("stores.id"), nullable=True
    )
    to_godown_id: Mapped[int | None] = mapped_column(
        ForeignKey("godowns.id"), nullable=True
    )
    reference_type: Mapped[str | None] = mapped_column(String, nullable=True)
    reference_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    performed_by_employee_id: Mapped[int | None] = mapped_column(
        ForeignKey("employees.id"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )