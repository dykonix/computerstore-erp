from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProductAttributeValueCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attribute_id: int
    attribute_option_id: int | None = None
    text_value: str | None = None
    number_value: int | None = None
    decimal_value: Decimal | None = None


class ProductCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sku: str
    name: str
    category_id: int
    brand_id: int
    description: str | None = None
    is_active: bool = True
    attributes: list[ProductAttributeValueCreate] = Field(default_factory=list)


class CategorySummary(BaseModel):
    id: int
    name: str


class BrandSummary(BaseModel):
    id: int
    name: str


class AttributeSummary(BaseModel):
    id: int
    name: str
    data_type: str
    unit: str | None


class AttributeOptionSummary(BaseModel):
    id: int
    attribute_id: int
    value: str
    display_order: int


class CategoryAttributeSummary(BaseModel):
    category_id: int
    attribute_id: int
    is_required: bool
    display_order: int


class ProductFormDataResponse(BaseModel):
    categories: list[CategorySummary]
    brands: list[BrandSummary]
    attributes: list[AttributeSummary]
    attribute_options: list[AttributeOptionSummary]
    category_attributes: list[CategoryAttributeSummary]


class ProductListItem(BaseModel):
    id: int
    sku: str
    name: str
    category: CategorySummary
    brand: BrandSummary
    is_active: bool


class ProductListResponse(BaseModel):
    items: list[ProductListItem]
    page: int
    page_size: int
    total: int


class ProductAttributeValueResponse(BaseModel):
    id: int
    attribute_id: int
    attribute_name: str
    data_type: str
    unit: str | None
    attribute_option_id: int | None
    attribute_option_value: str | None
    text_value: str | None
    number_value: int | None
    decimal_value: Decimal | None


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    name: str
    description: str | None
    category: CategorySummary
    brand: BrandSummary
    is_active: bool
    attributes: list[ProductAttributeValueResponse]


class ProductPriceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cost_price: Decimal = Field(default=Decimal("0.00"), ge=0)
    sale_price: Decimal = Field(ge=0)
    minimum_sale_price: Decimal | None = Field(default=None, ge=0)
    valid_from: date
    valid_to: date | None = None

    @model_validator(mode="after")
    def validate_price_period(self) -> "ProductPriceCreate":
        if (
            self.minimum_sale_price is not None
            and self.minimum_sale_price > self.sale_price
        ):
            raise ValueError("minimum_sale_price cannot exceed sale_price")
        if self.valid_to is not None and self.valid_to < self.valid_from:
            raise ValueError("valid_to cannot be earlier than valid_from")
        return self


class ProductPriceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cost_price: Decimal | None = Field(default=None, ge=0)
    sale_price: Decimal | None = Field(default=None, ge=0)
    minimum_sale_price: Decimal | None = Field(default=None, ge=0)
    valid_from: date | None = None
    valid_to: date | None = None


class ProductPriceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    cost_price: Decimal
    sale_price: Decimal
    minimum_sale_price: Decimal | None
    valid_from: date
    valid_to: date | None
    created_at: datetime
    updated_at: datetime