from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


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