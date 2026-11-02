"""Legacy table name retained; location assignments belong to users, not employees."""
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class EmployeeGodown(Base):
    __tablename__ = "employee_godowns"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    godown_id: Mapped[int] = mapped_column(
        ForeignKey("godowns.id"), primary_key=True
    )


# Transitional alias for code that should use the user-based name.
UserGodown = EmployeeGodown
