from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class SaleItemSerialNumber(Base):
    __tablename__ = "sale_item_serial_numbers"

    __table_args__ = (
        UniqueConstraint(
            "sale_item_id",
            "product_serial_number_id",
            name="uq_sale_item_serial_number_pair",
        ),
        UniqueConstraint(
            "product_serial_number_id",
            name="uq_sale_item_serial_number_serial",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    sale_item_id: Mapped[int] = mapped_column(
        ForeignKey("sale_items.id"),
        nullable=False,
    )

    product_serial_number_id: Mapped[int] = mapped_column(
        ForeignKey("product_serial_numbers.id"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )