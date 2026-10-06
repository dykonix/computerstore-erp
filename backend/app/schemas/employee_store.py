from pydantic import BaseModel, ConfigDict


class EmployeeStoreAssignmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    employee_id: int
    store_id: int