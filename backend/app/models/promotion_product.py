from sqlalchemy import ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class PromotionProduct(Base):
    __tablename__ = "promotion_products"

    __table_args__ = (
        PrimaryKeyConstraint(
            "promotion_id",
            "product_id",
            name="pk_promotion_products",
        ),
    )

    promotion_id: Mapped[int] = mapped_column(
        ForeignKey("promotions.id"),
        nullable=False,
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"),
        nullable=False,
    )