from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PromotionCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    valid_from: date
    valid_to: date
    is_active: bool = True


class PromotionUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    valid_from: date
    valid_to: date
    is_active: bool


class PromotionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    name: str
    valid_from: date
    valid_to: date
    is_active: bool


class PromotionProductRequest(BaseModel):
    product_id: int


class PromotionProductsRequest(BaseModel):
    product_ids: list[int]


class PromotionProductResponse(BaseModel):
    product_id: int


class ProductPromotionResponse(BaseModel):
    id: int
    name: str
    cashback_amount: Decimal


class PromotionGroupCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    selection_rule: str


class PromotionGroupUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    selection_rule: str


class PromotionGroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    promotion_id: int
    name: str
    selection_rule: str


class ProductBenefitRequest(BaseModel):
    product_id: int
    promotion_price: Decimal = Field(ge=0)


class WarrantyBenefitRequest(BaseModel):
    warranty_option_id: int
    promotion_price: Decimal = Field(ge=0)


class CashbackBenefitRequest(BaseModel):
    cashback_amount: Decimal = Field(ge=0)
    payment_mode: str


class PromotionBenefitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    promotion_group_id: int
    benefit_type: str
    product_id: int | None
    warranty_option_id: int | None
    promotion_price: Decimal | None
    cashback_amount: Decimal | None
    payment_mode: str | None