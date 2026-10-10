from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class PromotionProduct(Base):
    __tablename__ = "promotion_products"

    promotion_id: Mapped[int] = mapped_column(
        ForeignKey("promotions.id"),
        primary_key=True,
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"),
        primary_key=True,
    )