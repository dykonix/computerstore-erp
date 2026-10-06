from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class WarrantyOptionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: int
    additional_months: int = Field(gt=0)


class WarrantyOptionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    additional_months: int | None = Field(default=None, gt=0)


class WarrantyOptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    additional_months: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class WarrantyPriceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    price: Decimal = Field(ge=0)
    valid_from: date
    valid_to: date | None = None

    @model_validator(mode="after")
    def validate_validity_period(self) -> "WarrantyPriceCreate":
        if self.valid_to is not None and self.valid_to < self.valid_from:
            raise ValueError("valid_to cannot be earlier than valid_from")
        return self


class WarrantyPriceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    price: Decimal | None = Field(default=None, ge=0)
    valid_from: date | None = None
    valid_to: date | None = None


class WarrantyPriceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    warranty_option_id: int
    price: Decimal
    valid_from: date
    valid_to: date | None
    created_at: datetime
    updated_at: datetime