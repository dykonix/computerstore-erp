from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_tenant_id
from app.database.session import get_db
from app.schemas.supplier import (
    SupplierCreate,
    SupplierListResponse,
    SupplierResponse,
    SupplierUpdate,
)
from app.services.supplier_service import (
    SupplierNotFoundError,
    SupplierService,
    SupplierValidationError,
)

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


def _service() -> SupplierService:
    return SupplierService()


@router.post("", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
def create_supplier(
    request: SupplierCreate,
    session: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    service: SupplierService = Depends(_service),
) -> SupplierResponse:
    try:
        supplier = service.create_supplier(session, tenant_id, request)
        return SupplierResponse.model_validate(supplier)
    except SupplierValidationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("", response_model=SupplierListResponse)
def list_suppliers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_active: bool | None = Query(None),
    session: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    service: SupplierService = Depends(_service),
) -> SupplierListResponse:
    suppliers, total = service.list_suppliers(
        session, tenant_id, page, page_size, is_active
    )
    return SupplierListResponse(
        items=[SupplierResponse.model_validate(item) for item in suppliers],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/{supplier_id}", response_model=SupplierResponse)
def get_supplier(
    supplier_id: int,
    session: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    service: SupplierService = Depends(_service),
) -> SupplierResponse:
    try:
        supplier = service.get_supplier(session, tenant_id, supplier_id)
        return SupplierResponse.model_validate(supplier)
    except SupplierNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.put("/{supplier_id}", response_model=SupplierResponse)
def update_supplier(
    supplier_id: int,
    request: SupplierUpdate,
    session: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    service: SupplierService = Depends(_service),
) -> SupplierResponse:
    try:
        supplier = service.update_supplier(session, tenant_id, supplier_id, request)
        return SupplierResponse.model_validate(supplier)
    except SupplierNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except SupplierValidationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error