from pydantic import BaseModel, ConfigDict, Field


class UserIdentityCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1)
    email: str
    mobile: str
    employee_id: int | None = None


class UserIdentityUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str | None = None
    mobile: str | None = None
    employee_id: int | None = None