from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.sale import Sale


class SaleItem(Base):
    __tablename__ = "sale_items"

    __table_args__ = (
        UniqueConstraint(
            "sale_id",
            "promotion_source_sale_item_id",
            "promotion_benefit_id",
            name="uq_sale_items_sale_promotion_benefit",
        ),
        CheckConstraint(
            "quantity > 0",
            name="ck_sale_items_quantity_positive",
        ),
        CheckConstraint(
            "configured_unit_price >= 0",
            name="ck_sale_items_configured_price_nonnegative",
        ),
        CheckConstraint(
            "configured_minimum_price >= 0",
            name="ck_sale_items_minimum_price_nonnegative",
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
        CheckConstraint(
            "promotion_cashback_amount >= 0",
            name="ck_sale_items_promotion_cashback_nonnegative",
        ),
        CheckConstraint(
            "(is_promotion_benefit = false AND promotion_benefit_id IS NULL "
            "AND promotion_source_sale_item_id IS NULL "
            "AND promotion_benefit_source IS NULL) OR "
            "(is_promotion_benefit = true AND promotion_benefit_id IS NOT NULL "
            "AND promotion_benefit_name IS NOT NULL "
            "AND promotion_source_sale_item_id IS NOT NULL "
            "AND promotion_benefit_source IN ('STORE', 'MANUFACTURER'))",
            name="ck_sale_items_promotion_benefit_metadata",
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

    sale: Mapped["Sale"] = relationship(
        "Sale",
        back_populates="items",
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"),
        nullable=False,
    )

    promotion_id: Mapped[int | None] = mapped_column(
        ForeignKey("promotions.id"),
        nullable=True,
    )

    promotion_name: Mapped[str | None] = mapped_column(
        nullable=True,
    )

    promotion_cashback_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    promotion_benefit_id: Mapped[int | None] = mapped_column(nullable=True)
    promotion_benefit_name: Mapped[str | None] = mapped_column(nullable=True)
    promotion_source_sale_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("sale_items.id"), nullable=True
    )
    promotion_benefit_source: Mapped[str | None] = mapped_column(nullable=True)
    is_promotion_benefit: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    quantity: Mapped[int] = mapped_column(
        nullable=False,
    )

    configured_unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    configured_minimum_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    actual_unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    minimum_price_override: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    is_free_product: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
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