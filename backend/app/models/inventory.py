from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Inventory(Base):
    __tablename__ = "inventory"
    __table_args__ = (
        CheckConstraint(
            "(store_id IS NOT NULL) <> (godown_id IS NOT NULL)",
            name="ck_inventory_exactly_one_location",
        ),
        CheckConstraint(
            "quantity >= 0", name="ck_inventory_quantity_nonnegative"
        ),
        CheckConstraint(
            "reserved_quantity >= 0",
            name="ck_inventory_reserved_quantity_nonnegative",
        ),
        CheckConstraint(
            "reserved_quantity <= quantity",
            name="ck_inventory_reserved_quantity_lte_quantity",
        ),
        Index("ix_inventory_tenant_id", "tenant_id"),
        Index(
            "uq_inventory_tenant_product_store",
            "tenant_id",
            "product_id",
            "store_id",
            unique=True,
            postgresql_where=text("store_id IS NOT NULL"),
        ),
        Index(
            "uq_inventory_tenant_product_godown",
            "tenant_id",
            "product_id",
            "godown_id",
            unique=True,
            postgresql_where=text("godown_id IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"), nullable=False
    )
    store_id: Mapped[int | None] = mapped_column(
        ForeignKey("stores.id"), nullable=True
    )
    godown_id: Mapped[int | None] = mapped_column(
        ForeignKey("godowns.id"), nullable=True
    )
    quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    reserved_quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )