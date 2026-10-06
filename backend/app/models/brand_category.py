from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class BrandCategory(Base):
    __tablename__ = "brand_categories"

    brand_id: Mapped[int] = mapped_column(
        ForeignKey("brands.id"), primary_key=True
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id"), primary_key=True
    )