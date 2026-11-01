from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_auth_db, get_current_tenant, get_current_user, require_permission
from app.models.user import User
from app.services.authorization_service import AuthorizationService, PermissionDeniedError
from app.database.session import get_db
from app.repositories.inventory_repository import InventoryRepository
from app.schemas.inventory import InventoryCostPriceUpdate, InventoryFormDataResponse, InventoryListItem, InventoryListResponse, InventoryLocationSummary, InventoryResponse, InventoryTransferCreate, OpeningStockCreate
from app.services.inventory_service import InventoryNotFoundError, InventoryService, InventoryValidationError

router = APIRouter(prefix="/inventory", tags=["inventory"])
_inventory_view = Depends(require_permission("inventory.view"))
_inventory_manage = Depends(require_permission("inventory.manage"))


def _require_location_access(session, user, permission, store_id=None, godown_id=None):
    try:
        AuthorizationService().require_permission(session, user, permission, store_id=store_id, godown_id=godown_id)
    except PermissionDeniedError as error:
        raise HTTPException(status_code=403, detail="Permission denied for this inventory location") from error


def _service() -> InventoryService:
    return InventoryService()


def _row_response(row) -> InventoryResponse:
    inventory, product_name, sku, brand, category, location_type, location_name = row
    return InventoryResponse(id=inventory.id, product_id=inventory.product_id, store_id=inventory.store_id, godown_id=inventory.godown_id, product_name=product_name, sku=sku, brand=brand, category=category, location=InventoryLocationSummary(type=location_type, name=location_name), quantity=inventory.quantity, reserved_quantity=inventory.reserved_quantity, available_quantity=inventory.quantity - inventory.reserved_quantity, cost_price=inventory.cost_price)


@router.get("/form-data", response_model=InventoryFormDataResponse)
def inventory_form_data(session: Session = Depends(get_db), auth_session: Session = Depends(get_auth_db), current_user: User = Depends(get_current_user), tenant_id: int = Depends(get_current_tenant), _permission=_inventory_view) -> InventoryFormDataResponse:
    repository = InventoryRepository()
    authorization = AuthorizationService()
    try:
        stores = authorization.list_allowed_stores(auth_session, current_user, "inventory.view")
        godowns = authorization.list_allowed_godowns(auth_session, current_user, "inventory.view")
    except PermissionDeniedError as error:
        raise HTTPException(status_code=403, detail="Permission denied") from error
    return InventoryFormDataResponse(
        products=[{"id": item.id, "name": item.name, "sku": item.sku} for item in repository.list_products(session, tenant_id)],
        stores=[{"id": item.id, "name": item.name} for item in stores],
        godowns=[{"id": item.id, "name": item.name} for item in godowns],
    )


@router.post("/opening", response_model=InventoryResponse, status_code=status.HTTP_201_CREATED)
def create_opening_stock(request: OpeningStockCreate, session: Session = Depends(get_db), auth_session: Session = Depends(get_auth_db), current_user: User = Depends(get_current_user), tenant_id: int = Depends(get_current_tenant), service: InventoryService = Depends(_service), _permission=_inventory_manage) -> InventoryResponse:
    _require_location_access(auth_session, current_user, "inventory.manage", store_id=request.store_id, godown_id=request.godown_id)
    try:
        inventory = service.create_opening_stock(session, tenant_id, request)
        return _row_response(service.get_inventory(session, tenant_id, inventory.id))
    except InventoryValidationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/transfer", response_model=InventoryResponse, status_code=status.HTTP_201_CREATED)
def transfer_inventory(request: InventoryTransferCreate, session: Session = Depends(get_db), auth_session: Session = Depends(get_auth_db), current_user: User = Depends(get_current_user), tenant_id: int = Depends(get_current_tenant), service: InventoryService = Depends(_service), _permission=_inventory_manage) -> InventoryResponse:
    _require_location_access(auth_session, current_user, "inventory.manage", store_id=request.source_store_id, godown_id=request.source_godown_id)
    _require_location_access(auth_session, current_user, "inventory.manage", store_id=request.destination_store_id, godown_id=request.destination_godown_id)
    try:
        destination = service.transfer_inventory(session, tenant_id, request)
        return _row_response(service.get_inventory(session, tenant_id, destination.id))
    except InventoryValidationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("", response_model=InventoryListResponse)
def list_inventory(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), product_id: int | None = Query(None, gt=0), store_id: int | None = Query(None, gt=0), session: Session = Depends(get_db), tenant_id: int = Depends(get_current_tenant), service: InventoryService = Depends(_service)) -> InventoryListResponse:
    rows, total = service.list_inventory(session, tenant_id, page, page_size, product_id, store_id)
    return InventoryListResponse(items=[_row_response(row) for row in rows], page=page, page_size=page_size, total=total)


@router.get("/{inventory_id}", response_model=InventoryResponse)
def get_inventory(inventory_id: int, session: Session = Depends(get_db), tenant_id: int = Depends(get_current_tenant), service: InventoryService = Depends(_service)) -> InventoryResponse:
    try:
        return _row_response(service.get_inventory(session, tenant_id, inventory_id))
    except InventoryNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.put("/{inventory_id}", response_model=InventoryResponse)
def update_inventory_cost_price(inventory_id: int, request: InventoryCostPriceUpdate, session: Session = Depends(get_db), tenant_id: int = Depends(get_current_tenant), service: InventoryService = Depends(_service)) -> InventoryResponse:
    try:
        service.update_inventory_cost_price(session, tenant_id, inventory_id, request)
        return _row_response(service.get_inventory(session, tenant_id, inventory_id))
    except InventoryNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error