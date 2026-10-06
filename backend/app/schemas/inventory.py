from pydantic import BaseModel, ConfigDict, Field, model_validator


class OpeningStockCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: int
    supplier_id: int
    store_id: int | None = None
    godown_id: int | None = None
    quantity: int = Field(gt=0)


class InventoryTransferCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: int
    source_store_id: int | None = None
    source_godown_id: int | None = None
    destination_store_id: int | None = None
    destination_godown_id: int | None = None
    quantity: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_location_pairs(self) -> "InventoryTransferCreate":
        if (self.source_store_id is None) == (self.source_godown_id is None):
            raise ValueError("Exactly one source store_id or godown_id is required")
        if (self.destination_store_id is None) == (self.destination_godown_id is None):
            raise ValueError("Exactly one destination store_id or godown_id is required")
        return self


class InventoryLocationSummary(BaseModel):
    type: str
    name: str


class InventoryListItem(BaseModel):
    id: int
    product_id: int
    product_name: str
    sku: str
    brand: str
    category: str
    location: InventoryLocationSummary
    quantity: int
    reserved_quantity: int
    available_quantity: int


class InventoryListResponse(BaseModel):
    items: list[InventoryListItem]
    page: int
    page_size: int
    total: int


class InventoryResponse(InventoryListItem):
    pass


class InventoryFormDataResponse(BaseModel):
    products: list[dict[str, object]]
    stores: list[dict[str, object]]
    godowns: list[dict[str, object]]