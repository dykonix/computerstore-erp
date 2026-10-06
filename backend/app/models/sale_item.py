from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class SaleItem(Base):
    __tablename__ = "sale_items"
    __table_args__ = (
        CheckConstraint(
            "quantity > 0",
            name="ck_sale_items_quantity_positive",
        ),
        CheckConstraint(
            "configured_unit_price >= 0",
            name="ck_sale_items_configured_price_nonnegative",
        ),
        CheckConstraint(
            "actual_unit_price >= 0",
            name="ck_sale_items_actual_price_nonnegative",
        ),
        CheckConstraint(
            "cost_price >= 0",
            name="ck_sale_items_cost_price_nonnegative",
        ),
        CheckConstraint(
            "gst_rate >= 0",
            name="ck_sale_items_gst_rate_nonnegative",
        ),
        CheckConstraint(
            "gst_amount >= 0",
            name="ck_sale_items_gst_amount_nonnegative",
        ),
        CheckConstraint(
            "discount_amount >= 0",
            name="ck_sale_items_discount_nonnegative",
        ),
        CheckConstraint(
            "line_total >= 0",
            name="ck_sale_items_line_total_nonnegative",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    sale_id: Mapped[int] = mapped_column(
        ForeignKey("sales.id"),
        nullable=False,
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"),
        nullable=False,
    )

    quantity: Mapped[int] = mapped_column(
        nullable=False,
    )

    configured_unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    actual_unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    cost_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    gst_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )

    gst_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    line_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
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