from pydantic import BaseModel, ConfigDict, Field


class UserIdentityCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1)
    email: str
    mobile: str
    employee_id: int | None = None
    role_ids: list[int] = Field(default_factory=list, max_length=20)
    store_ids: list[int] | None = Field(default=None, max_length=20)
    godown_ids: list[int] | None = Field(default=None, max_length=20)


class UserIdentityUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str | None = None
    mobile: str | None = None
    employee_id: int | None = None