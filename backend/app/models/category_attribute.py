from sqlalchemy import ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class CategoryAttribute(Base):
    __tablename__ = "category_attributes"

    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id"), primary_key=True
    )
    attribute_id: Mapped[int] = mapped_column(
        ForeignKey("attributes.id"), primary_key=True
    )
    is_required: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default=text("false")
    )
    display_order: Mapped[int] = mapped_column(
        nullable=False, default=0, server_default=text("0")
    )