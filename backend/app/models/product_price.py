from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, CheckConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ProductPrice(Base):
    __tablename__ = "product_prices"

    __table_args__ = (
        CheckConstraint(
            "cost_price >= 0",
            name="ck_product_prices_cost_price_nonnegative",
        ),
        CheckConstraint(
            "sale_price >= 0",
            name="ck_product_prices_sale_price_nonnegative",
        ),
        CheckConstraint(
            "minimum_sale_price IS NULL OR minimum_sale_price >= 0",
            name="ck_product_prices_minimum_sale_price_nonnegative",
        ),
        CheckConstraint(
            "minimum_sale_price IS NULL OR minimum_sale_price <= sale_price",
            name="ck_product_prices_minimum_lte_sale",
        ),
        CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_product_prices_valid_dates",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"),
        nullable=False,
    )

    cost_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    sale_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    minimum_sale_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    valid_from: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    valid_to: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
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