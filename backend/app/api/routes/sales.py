from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.database.session import get_db
from app.models.product import Product
from app.models.user import User
from app.schemas.sale import (
    SaleCreate,
    SaleItemCreate,
    SaleItemResponse,
    SalePaymentCreate,
    SalePaymentResponse,
    SaleDeliveryRequest,
    ProductAvailabilityResponse,
    SaleResponse,
)
from app.services.sale_service import SaleService
from app.services.authorization_service import PermissionDeniedError
from app.repositories.sale_repository import SaleRepository


router = APIRouter(
    prefix="/sales",
    tags=["sales"],
)


def _sale_response(session: Session, sale) -> SaleResponse:
    response = SaleResponse.model_validate(sale)
    repository = SaleRepository()
    return response.model_copy(
        update={
            "items": [
                item.model_copy(
                    update={
                        "serial_numbers": [
                            serial.serial_number
                            for serial in repository.list_sale_item_serials(
                                session, item.id
                            )
                        ],
                        "requires_serial_number": bool(
                            (product := session.get(Product, item.product_id))
                            and product.requires_serial_number
                        ),
                    }
                )
                for item in response.items
            ]
        }
    )


def _service() -> SaleService:
    return SaleService()


@router.post(
    "",
    response_model=SaleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_sale(
    request: SaleCreate,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        sale = _service().create_sale(
            session=session,
            current_user=current_user,
            store_id=request.store_id,
            customer_id=request.customer_id,
        )
        return _sale_response(session, sale)
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error


@router.get(
    "/availability/{product_id}",
    response_model=ProductAvailabilityResponse,
)
def get_product_availability(
    product_id: int,
    store_id: int,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return _service().get_product_availability(
            session=session,
            current_user=current_user,
            store_id=store_id,
            product_id=product_id,
        )
    except PermissionDeniedError as error:
        raise HTTPException(status_code=403, detail="Permission denied") from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get(
    "/{sale_id}",
    response_model=SaleResponse,
    status_code=status.HTTP_200_OK,
)
def get_sale(
    sale_id: int,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sale = _service().get_sale(
        session=session,
        current_user=current_user,
        sale_id=sale_id,
    )

    if sale is None:
        raise HTTPException(
            status_code=404,
            detail="Sale not found",
        )

    return _sale_response(session, sale)


@router.post(
    "/{sale_id}/items",
    response_model=SaleItemResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_sale_item(
    sale_id: int,
    request: SaleItemCreate,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return _service().add_sale_item(
            session=session,
            current_user=current_user,
            sale_id=sale_id,
            product_id=request.product_id,
            quantity=request.quantity,
            actual_unit_price=request.actual_unit_price,
            configured_minimum_price=request.configured_minimum_price,
            minimum_price_override=request.minimum_price_override,
            is_free_product=request.is_free_product,
            promotion_id=request.promotion_id,
            promotion_benefit_ids=request.promotion_benefit_ids,
            promotion_benefit_ids_by_unit=request.promotion_benefit_ids_by_unit,
            promotion_benefit_sources_by_unit=request.promotion_benefit_sources_by_unit,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error


@router.post(
    "/{sale_id}/reserve",
    response_model=SaleResponse,
    status_code=status.HTTP_200_OK,
)
def reserve_sale(
    sale_id: int,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        sale = _service().reserve_sale(
            session,
            current_user,
            sale_id,
        )
        return _sale_response(session, sale)
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error


@router.get(
    "/{sale_id}/payments",
    response_model=list[SalePaymentResponse],
)
def list_sale_payments(
    sale_id: int,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return _service().list_sale_payments(
            session=session,
            current_user=current_user,
            sale_id=sale_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post(
    "/{sale_id}/payments",
    response_model=SalePaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_sale_payment(
    sale_id: int,
    request: SalePaymentCreate,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return _service().add_sale_payment(
            session=session,
            current_user=current_user,
            sale_id=sale_id,
            payment_mode=request.payment_mode,
            amount=request.amount,
            transaction_reference=request.transaction_reference,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post(
    "/{sale_id}/confirm",
    response_model=SaleResponse,
)
def confirm_sale(
    sale_id: int,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        sale = _service().confirm_sale(
            session=session,
            current_user=current_user,
            sale_id=sale_id,
        )
        return _sale_response(session, sale)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post(
    "/{sale_id}/deliver",
    response_model=SaleResponse,
)
def deliver_sale(
    sale_id: int,
    request: SaleDeliveryRequest | None = None,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        sale = _service().deliver_sale(
            session=session,
            current_user=current_user,
            sale_id=sale_id,
            serial_numbers_by_item=(
                request.serial_numbers_by_item if request is not None else None
            ),
            allow_missing_serial_numbers=(
                request.allow_missing_serial_numbers if request is not None else True
            ),
        )
        return _sale_response(session, sale)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error