from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class SaleCreate(BaseModel):
    store_id: int = Field(gt=0)
    customer_id: int | None = Field(default=None, gt=0)


class SaleItemCreate(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)
    actual_unit_price: Decimal | None = Field(default=None, ge=0)


class SaleItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sale_id: int
    product_id: int
    quantity: int
    configured_unit_price: Decimal
    actual_unit_price: Decimal
    cost_price: Decimal
    gst_rate: Decimal
    gst_amount: Decimal
    discount_amount: Decimal
    line_total: Decimal


class SaleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    store_id: int
    customer_id: int | None
    employee_id: int
    status: str
    reserved_at: datetime | None
    reservation_warning_at: datetime | None
    reservation_expires_at: datetime | None
    subtotal: Decimal
    invoice_discount: Decimal
    taxable_amount: Decimal
    gst_amount: Decimal
    total_amount: Decimal