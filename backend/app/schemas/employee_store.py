from pydantic import BaseModel, ConfigDict


class EmployeeStoreAssignmentCreate(BaseModel):
    """Legacy schema name; assignment is made for a user."""
    model_config = ConfigDict(extra="forbid")

    user_id: int
    store_id: int
