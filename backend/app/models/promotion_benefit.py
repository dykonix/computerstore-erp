from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class PromotionBenefit(Base):
    __tablename__ = "promotion_benefits"

    __table_args__ = (
        CheckConstraint(
            "benefit_type IN ('PRODUCT', 'WARRANTY', 'CASHBACK')",
            name="ck_promotion_benefits_type",
        ),
        CheckConstraint(
            "cashback_amount IS NULL OR cashback_amount >= 0",
            name="ck_promotion_benefits_cashback_nonnegative",
        ),
        CheckConstraint(
            "promotion_price IS NULL OR promotion_price >= 0",
            name="ck_promotion_benefits_price_nonnegative",
        ),
        CheckConstraint(
            """
            (
                benefit_type = 'PRODUCT'
                AND product_id IS NOT NULL
                AND warranty_option_id IS NULL
                AND promotion_price IS NOT NULL
                AND cashback_amount IS NULL
                AND payment_mode IS NULL
            )
            OR
            (
                benefit_type = 'WARRANTY'
                AND product_id IS NULL
                AND warranty_option_id IS NOT NULL
                AND promotion_price IS NOT NULL
                AND cashback_amount IS NULL
                AND payment_mode IS NULL
            )
            OR
            (
                benefit_type = 'CASHBACK'
                AND product_id IS NULL
                AND warranty_option_id IS NULL
                AND promotion_price IS NULL
                AND cashback_amount IS NOT NULL
                AND payment_mode IS NOT NULL
            )
            """,
            name="ck_promotion_benefits_valid_type_fields",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    promotion_group_id: Mapped[int] = mapped_column(
        ForeignKey("promotion_groups.id"),
        nullable=False,
    )

    benefit_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id"),
        nullable=True,
    )

    warranty_option_id: Mapped[int | None] = mapped_column(
        ForeignKey("warranty_options.id"),
        nullable=True,
    )

    promotion_price: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=12, scale=2),
        nullable=True,
    )

    cashback_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=12, scale=2),
        nullable=True,
    )

    payment_mode: Mapped[str | None] = mapped_column(
        String,
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
    )