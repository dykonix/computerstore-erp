from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class PromotionGroup(Base):
    __tablename__ = "promotion_groups"

    __table_args__ = (
        CheckConstraint(
            "selection_rule IN ('REQUIRED', 'ONE', 'ALL', 'OPTIONAL')",
            name="ck_promotion_groups_selection_rule",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    promotion_id: Mapped[int] = mapped_column(
        ForeignKey("promotions.id"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    selection_rule: Mapped[str] = mapped_column(
        String,
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