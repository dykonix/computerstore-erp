from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Sale(Base):
    __tablename__ = "sales"
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'RESERVED', 'CONFIRMED', 'PICKED', 'ASSEMBLY', 'DELIVERED', 'CANCELLED')",
            name="ck_sales_status",
        ),
        CheckConstraint(
            "subtotal >= 0",
            name="ck_sales_subtotal_nonnegative",
        ),
        CheckConstraint(
            "invoice_discount >= 0",
            name="ck_sales_invoice_discount_nonnegative",
        ),
        CheckConstraint(
            "taxable_amount >= 0",
            name="ck_sales_taxable_amount_nonnegative",
        ),
        CheckConstraint(
            "gst_amount >= 0",
            name="ck_sales_gst_amount_nonnegative",
        ),
        CheckConstraint(
            "total_amount >= 0",
            name="ck_sales_total_amount_nonnegative",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id"),
        nullable=False,
    )

    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.id"),
        nullable=False,
    )

    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id"),
        nullable=True,
    )

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="DRAFT",
        server_default=text("'DRAFT'"),
    )

    reserved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    reservation_warning_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    reservation_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    invoice_discount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    taxable_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    gst_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )