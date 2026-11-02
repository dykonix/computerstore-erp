"""User-facing alias for the existing employee_godowns table; no new table is created."""
from app.models.employee_godown import EmployeeGodown as UserGodown

__all__ = ["UserGodown"]
