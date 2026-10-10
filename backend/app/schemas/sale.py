from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SaleCreate(BaseModel):
    store_id: int = Field(gt=0)
    customer_id: int | None = Field(default=None, gt=0)


class SaleItemCreate(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)
    actual_unit_price: Decimal | None = Field(default=None, ge=0)
    configured_minimum_price: Decimal = Field(default=Decimal("0"), ge=0)
    minimum_price_override: bool = False
    is_free_product: bool = False
    promotion_id: int | None = Field(default=None, gt=0)


class SaleItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sale_id: int
    product_id: int
    quantity: int
    configured_unit_price: Decimal
    configured_minimum_price: Decimal
    actual_unit_price: Decimal
    minimum_price_override: bool
    is_free_product: bool
    promotion_id: int | None
    promotion_name: str | None
    promotion_cashback_amount: Decimal
    cost_price: Decimal
    gst_rate: Decimal
    gst_amount: Decimal
    discount_amount: Decimal
    line_total: Decimal


class SaleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    store_id: int
    customer_id: int | None
    employee_id: int
    status: Literal["DRAFT", "RESERVED", "CONFIRMED", "DELIVERED"]
    reserved_at: datetime | None
    reservation_warning_at: datetime | None
    reservation_expires_at: datetime | None
    subtotal: Decimal
    invoice_discount: Decimal
    taxable_amount: Decimal
    gst_amount: Decimal
    total_amount: Decimal
    payable_amount: Decimal
    cashback_amount: Decimal
    items: list[SaleItemResponse] = Field(default_factory=list)


class SalePaymentCreate(BaseModel):
    payment_mode: str = Field(min_length=1)
    amount: Decimal = Field(gt=0)
    transaction_reference: str | None = None


class SalePaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sale_id: int
    payment_mode: str
    amount: Decimal
    transaction_reference: str | None
    paid_at: datetime