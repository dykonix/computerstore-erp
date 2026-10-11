from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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
    promotion_benefit_ids: list[int] = Field(default_factory=list)
    promotion_benefit_ids_by_unit: list[list[int]] | None = None
    promotion_benefit_sources_by_unit: list[dict[int, Literal["STORE", "MANUFACTURER"]]] | None = None

    @field_validator("promotion_benefit_ids")
    @classmethod
    def validate_unique_promotion_benefits(cls, value: list[int]) -> list[int]:
        if len(value) != len(set(value)):
            raise ValueError("Promotion benefit IDs must be unique")
        if any(benefit_id <= 0 for benefit_id in value):
            raise ValueError("Promotion benefit IDs must be positive")
        return value

    @model_validator(mode="after")
    def validate_unit_benefits(self) -> "SaleItemCreate":
        if self.promotion_benefit_ids_by_unit is not None:
            if len(self.promotion_benefit_ids_by_unit) != self.quantity:
                raise ValueError("Provide benefit selections for every product unit")
            if self.promotion_benefit_ids:
                raise ValueError("Use either per-unit or shared benefit IDs, not both")
            for benefit_ids in self.promotion_benefit_ids_by_unit:
                if len(benefit_ids) != len(set(benefit_ids)):
                    raise ValueError("A benefit cannot be duplicated for one unit")
                if any(benefit_id <= 0 for benefit_id in benefit_ids):
                    raise ValueError("Promotion benefit IDs must be positive")
        elif self.promotion_benefit_ids and self.quantity > 1:
            raise ValueError("Benefit selections must be supplied independently for each unit")

        if self.promotion_benefit_sources_by_unit is not None:
            if self.promotion_benefit_ids_by_unit is None:
                raise ValueError("Per-unit benefit sources require per-unit benefit IDs")
            if len(self.promotion_benefit_sources_by_unit) != self.quantity:
                raise ValueError("Provide benefit sources for every product unit")
            for benefit_ids, sources in zip(
                self.promotion_benefit_ids_by_unit,
                self.promotion_benefit_sources_by_unit,
            ):
                if set(sources) - set(benefit_ids):
                    raise ValueError("Benefit sources may only be set for selected product benefits")
        return self


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
    promotion_benefit_id: int | None = None
    promotion_benefit_name: str | None = None
    promotion_source_sale_item_id: int | None = None
    promotion_benefit_source: str | None = None
    is_promotion_benefit: bool = False
    requires_serial_number: bool = False
    serial_numbers: list[str] = Field(default_factory=list)
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


class LocationAvailability(BaseModel):
    location_type: str
    location_name: str
    quantity: int
    reserved_quantity: int
    available_quantity: int


class ProductAvailabilityResponse(BaseModel):
    current_store: LocationAvailability
    other_locations: list[LocationAvailability]


class SaleDeliveryRequest(BaseModel):
    serial_numbers_by_item: dict[int, list[str]] = Field(default_factory=dict)
    allow_missing_serial_numbers: bool = False

    @field_validator("serial_numbers_by_item")
    @classmethod
    def validate_serial_numbers(
        cls, value: dict[int, list[str]]
    ) -> dict[int, list[str]]:
        normalized: dict[int, list[str]] = {}
        for sale_item_id, serial_numbers in value.items():
            if sale_item_id <= 0:
                raise ValueError("Sale item IDs must be positive")
            cleaned = [serial.strip() for serial in serial_numbers]
            if any(not serial for serial in cleaned):
                raise ValueError("Serial numbers cannot be blank")
            if len(cleaned) != len(set(cleaned)):
                raise ValueError("Duplicate serial numbers are not allowed")
            normalized[sale_item_id] = cleaned
        return normalized