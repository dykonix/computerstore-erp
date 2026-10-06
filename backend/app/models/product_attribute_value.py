from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ProductAttributeValue(Base):
    __tablename__ = "product_attribute_values"
    __table_args__ = (
        Index(
            "uq_product_attribute_values_product_attribute_scalar",
            "product_id",
            "attribute_id",
            unique=True,
            postgresql_where=text("attribute_option_id IS NULL"),
            sqlite_where=text("attribute_option_id IS NULL"),
        ),
        Index(
            "uq_product_attribute_values_product_attribute_option",
            "product_id",
            "attribute_id",
            "attribute_option_id",
            unique=True,
            postgresql_where=text("attribute_option_id IS NOT NULL"),
            sqlite_where=text("attribute_option_id IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"), nullable=False, index=True
    )
    attribute_id: Mapped[int] = mapped_column(
        ForeignKey("attributes.id"), nullable=False, index=True
    )
    attribute_option_id: Mapped[int | None] = mapped_column(
        ForeignKey("attribute_options.id"), nullable=True, index=True
    )
    text_value: Mapped[str | None] = mapped_column(String, nullable=True)
    number_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    decimal_value: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 6), nullable=True
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