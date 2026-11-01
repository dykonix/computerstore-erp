from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class EmployeeGodown(Base):
    __tablename__ = "employee_godowns"

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id"), primary_key=True
    )
    godown_id: Mapped[int] = mapped_column(
        ForeignKey("godowns.id"), primary_key=True
    )
