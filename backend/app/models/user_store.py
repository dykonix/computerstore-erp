"""User-facing alias for the existing employee_stores table; no new table is created."""
from app.models.employee_store import EmployeeStore as UserStore

__all__ = ["UserStore"]
