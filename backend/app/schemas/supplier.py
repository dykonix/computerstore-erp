from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SupplierCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    contact_person: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    is_active: bool = True


class SupplierUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1)
    contact_person: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    is_active: bool | None = None


class SupplierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    contact_person: str | None
    phone: str | None
    email: str | None
    address: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SupplierListResponse(BaseModel):
    items: list[SupplierResponse]
    page: int
    page_size: int
    total: int