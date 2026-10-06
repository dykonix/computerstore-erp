from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    gst_rate: Decimal | None = Field(default=None, ge=0, le=100)


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    gst_rate: Decimal | None = Field(default=None, ge=0, le=100)


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    gst_rate: Decimal | None
    is_active: bool
    created_at: datetime
    updated_at: datetime