from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class PromotionGroup(Base):
    __tablename__ = "promotion_groups"

    __table_args__ = (
        CheckConstraint(
            "selection_rule IN ('REQUIRED', 'ONE', 'ALL', 'OPTIONAL')",
            name="ck_promotion_groups_selection_rule",
        ),
        CheckConstraint(
            "group_requirement IS NULL OR group_requirement IN ('REQUIRED', 'OPTIONAL')",
            name="ck_promotion_groups_group_requirement",
        ),
        CheckConstraint(
            "benefit_selection_rule IS NULL OR benefit_selection_rule IN ('ONE', 'ANY', 'ALL')",
            name="ck_promotion_groups_benefit_selection_rule",
        ),
        CheckConstraint(
            "(group_requirement IS NULL AND benefit_selection_rule IS NULL) OR "
            "(group_requirement IS NOT NULL AND benefit_selection_rule IS NOT NULL)",
            name="ck_promotion_groups_split_rules_paired",
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

    group_requirement: Mapped[str | None] = mapped_column(String, nullable=True)
    benefit_selection_rule: Mapped[str | None] = mapped_column(String, nullable=True)

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