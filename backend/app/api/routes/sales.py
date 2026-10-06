from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.sale import (
    SaleCreate,
    SaleItemCreate,
    SaleItemResponse,
    SaleResponse,
)
from app.services.sale_service import SaleService


router = APIRouter(
    prefix="/sales",
    tags=["sales"],
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
        return _service().create_sale(
            session=session,
            current_user=current_user,
            store_id=request.store_id,
            customer_id=request.customer_id,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error


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
        return _service().reserve_sale(
            session,
            current_user,
            sale_id,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error