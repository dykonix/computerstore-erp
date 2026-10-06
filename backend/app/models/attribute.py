from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Attribute(Base):
    __tablename__ = "attributes"
    __table_args__ = (
        CheckConstraint(
            "data_type IN ('SELECT', 'MULTI_SELECT', 'NUMBER', 'DECIMAL', 'TEXT')",
            name="ck_attributes_data_type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    data_type: Mapped[str] = mapped_column(String, nullable=False)
    unit: Mapped[str | None] = mapped_column(String, nullable=True)
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