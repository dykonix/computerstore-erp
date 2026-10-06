from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_tenant_id
from app.database.session import get_db
from app.repositories.inventory_repository import InventoryRepository
from app.schemas.inventory import InventoryFormDataResponse, InventoryListItem, InventoryListResponse, InventoryLocationSummary, InventoryResponse, InventoryTransferCreate, OpeningStockCreate
from app.services.inventory_service import InventoryNotFoundError, InventoryService, InventoryValidationError

router = APIRouter(prefix="/inventory", tags=["inventory"])


def _service() -> InventoryService:
    return InventoryService()


def _row_response(row) -> InventoryResponse:
    inventory, product_name, sku, brand, category, location_type, location_name = row
    return InventoryResponse(id=inventory.id, product_id=inventory.product_id, product_name=product_name, sku=sku, brand=brand, category=category, location=InventoryLocationSummary(type=location_type, name=location_name), quantity=inventory.quantity, reserved_quantity=inventory.reserved_quantity, available_quantity=inventory.quantity - inventory.reserved_quantity)


@router.get("/form-data", response_model=InventoryFormDataResponse)
def inventory_form_data(session: Session = Depends(get_db), tenant_id: int = Depends(get_current_tenant_id)) -> InventoryFormDataResponse:
    repository = InventoryRepository()
    return InventoryFormDataResponse(products=[{"id": item.id, "name": item.name, "sku": item.sku} for item in repository.list_products(session, tenant_id)], stores=[{"id": item.id, "name": item.name} for item in repository.list_stores(session, tenant_id)], godowns=[{"id": item.id, "name": item.name} for item in repository.list_godowns(session, tenant_id)])


@router.post("/opening", response_model=InventoryResponse, status_code=status.HTTP_201_CREATED)
def create_opening_stock(request: OpeningStockCreate, session: Session = Depends(get_db), tenant_id: int = Depends(get_current_tenant_id), service: InventoryService = Depends(_service)) -> InventoryResponse:
    try:
        inventory = service.create_opening_stock(session, tenant_id, request)
        return _row_response(service.get_inventory(session, tenant_id, inventory.id))
    except InventoryValidationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/transfer", response_model=InventoryResponse, status_code=status.HTTP_201_CREATED)
def transfer_inventory(request: InventoryTransferCreate, session: Session = Depends(get_db), tenant_id: int = Depends(get_current_tenant_id), service: InventoryService = Depends(_service)) -> InventoryResponse:
    try:
        destination = service.transfer_inventory(session, tenant_id, request)
        return _row_response(service.get_inventory(session, tenant_id, destination.id))
    except InventoryValidationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("", response_model=InventoryListResponse)
def list_inventory(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), session: Session = Depends(get_db), tenant_id: int = Depends(get_current_tenant_id), service: InventoryService = Depends(_service)) -> InventoryListResponse:
    rows, total = service.list_inventory(session, tenant_id, page, page_size)
    return InventoryListResponse(items=[_row_response(row) for row in rows], page=page, page_size=page_size, total=total)


@router.get("/{inventory_id}", response_model=InventoryResponse)
def get_inventory(inventory_id: int, session: Session = Depends(get_db), tenant_id: int = Depends(get_current_tenant_id), service: InventoryService = Depends(_service)) -> InventoryResponse:
    try:
        return _row_response(service.get_inventory(session, tenant_id, inventory_id))
    except InventoryNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error