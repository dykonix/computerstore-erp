from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class EmployeeStore(Base):
    __tablename__ = "employee_stores"

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id"), primary_key=True
    )
    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.id"), primary_key=True
    )