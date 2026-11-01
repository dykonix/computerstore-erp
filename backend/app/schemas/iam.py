from pydantic import BaseModel, ConfigDict, Field


class UserAdminCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=120)
    email: str
    mobile: str
    employee_id: int | None = None
    role_ids: list[int] = Field(default_factory=list, max_length=20)
    store_ids: list[int] | None = Field(default=None, max_length=20)
    initial_password: str = Field(min_length=12, max_length=128)


class UserStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_active: bool


class EmployeeOption(BaseModel):
    id: int
    name: str | None
    email: str


class RoleOption(BaseModel):
    id: int
    name: str


class StoreOption(BaseModel):
    id: int
    name: str
    employee_ids: list[int]


class UserAdminResponse(BaseModel):
    id: int
    username: str
    email: str
    mobile: str
    employee_id: int | None
    employee_name: str | None
    is_active: bool
    role_ids: list[int]
    role_names: list[str]


class UserFormDataResponse(BaseModel):
    employees: list[EmployeeOption]
    roles: list[RoleOption]
    stores: list[StoreOption]
