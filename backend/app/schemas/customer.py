from pydantic import BaseModel, ConfigDict, Field


class CustomerCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    mobile: str = Field(min_length=1)
    email: str | None = None
    address: str | None = None


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    mobile: str | None
    email: str | None
    address: str | None
    is_active: bool