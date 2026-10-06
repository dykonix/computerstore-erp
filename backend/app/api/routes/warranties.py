from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_tenant_id
from app.database.session import get_db
from app.schemas.warranty import (
    WarrantyOptionCreate,
    WarrantyOptionResponse,
    WarrantyOptionUpdate,
    WarrantyPriceCreate,
    WarrantyPriceResponse,
    WarrantyPriceUpdate,
)
from app.services.warranty_service import (
    WarrantyNotFoundError,
    WarrantyService,
    WarrantyValidationError,
)

router = APIRouter(prefix="/warranty-options", tags=["warranties"])


def _service() -> WarrantyService:
    return WarrantyService()


@router.get("", response_model=list[WarrantyOptionResponse])
def list_warranty_options(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    product_id: int | None = Query(None, ge=1),
    is_active: bool | None = Query(None),
    session: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    service: WarrantyService = Depends(_service),
) -> list[WarrantyOptionResponse]:
    options = service.list_options(
        session, tenant_id, page, page_size, product_id, is_active
    )
    return [WarrantyOptionResponse.model_validate(option) for option in options]


@router.post(
    "",
    response_model=WarrantyOptionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_warranty_option(
    request: WarrantyOptionCreate,
    session: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    service: WarrantyService = Depends(_service),
) -> WarrantyOptionResponse:
    try:
        option = service.create_option(session, tenant_id, request)
        return WarrantyOptionResponse.model_validate(option)
    except WarrantyValidationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/{option_id}", response_model=WarrantyOptionResponse)
def get_warranty_option(
    option_id: int,
    session: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    service: WarrantyService = Depends(_service),
) -> WarrantyOptionResponse:
    try:
        option = service.get_option(session, tenant_id, option_id)
        return WarrantyOptionResponse.model_validate(option)
    except WarrantyNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.put("/{option_id}", response_model=WarrantyOptionResponse)
def update_warranty_option(
    option_id: int,
    request: WarrantyOptionUpdate,
    session: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    service: WarrantyService = Depends(_service),
) -> WarrantyOptionResponse:
    try:
        option = service.update_option(session, tenant_id, option_id, request)
        return WarrantyOptionResponse.model_validate(option)
    except WarrantyNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except WarrantyValidationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.patch("/{option_id}/status", response_model=WarrantyOptionResponse)
def set_warranty_option_status(
    option_id: int,
    is_active: bool,
    session: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    service: WarrantyService = Depends(_service),
) -> WarrantyOptionResponse:
    try:
        option = service.set_option_status(
            session, tenant_id, option_id, is_active
        )
        return WarrantyOptionResponse.model_validate(option)
    except WarrantyNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/{option_id}/prices", response_model=list[WarrantyPriceResponse])
def list_warranty_prices(
    option_id: int,
    session: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    service: WarrantyService = Depends(_service),
) -> list[WarrantyPriceResponse]:
    try:
        prices = service.list_prices(session, tenant_id, option_id)
        return [WarrantyPriceResponse.model_validate(price) for price in prices]
    except WarrantyNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post(
    "/{option_id}/prices",
    response_model=WarrantyPriceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_warranty_price(
    option_id: int,
    request: WarrantyPriceCreate,
    session: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    service: WarrantyService = Depends(_service),
) -> WarrantyPriceResponse:
    try:
        price = service.create_price(session, tenant_id, option_id, request)
        return WarrantyPriceResponse.model_validate(price)
    except WarrantyValidationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.put("/prices/{price_id}", response_model=WarrantyPriceResponse)
def update_warranty_price(
    price_id: int,
    request: WarrantyPriceUpdate,
    session: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    service: WarrantyService = Depends(_service),
) -> WarrantyPriceResponse:
    try:
        price = service.update_price(session, tenant_id, price_id, request)
        return WarrantyPriceResponse.model_validate(price)
    except WarrantyNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except WarrantyValidationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error