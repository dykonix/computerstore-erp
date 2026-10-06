from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class AttributeOption(Base):
    __tablename__ = "attribute_options"
    __table_args__ = (
        UniqueConstraint(
            "attribute_id", "value", name="uq_attribute_options_attribute_value"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    attribute_id: Mapped[int] = mapped_column(
        ForeignKey("attributes.id"), nullable=False, index=True
    )
    value: Mapped[str] = mapped_column(String, nullable=False)
    display_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    is_active: Mapped[bool] = mapped_column(
        nullable=False, default=True, server_default=text("true")
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