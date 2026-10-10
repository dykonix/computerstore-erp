from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.customer import CustomerCreateRequest, CustomerResponse
from app.services.customer_service import CustomerService


router = APIRouter(
    prefix="/customers",
    tags=["customers"],
)


def _service() -> CustomerService:
    return CustomerService()


@router.get(
    "",
    response_model=list[CustomerResponse],
)
def list_active_customers(
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _service().list_active_customers(
        session=session,
        tenant_id=current_user.tenant_id,
    )


@router.get(
    "/search",
    response_model=list[CustomerResponse],
)
def search_customers(
    query: str = Query(..., min_length=1),
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _service().search_customers(
        session=session,
        tenant_id=current_user.tenant_id,
        query=query,
    )


@router.post(
    "",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_customer(
    request: CustomerCreateRequest,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        customer = _service().create_customer(
            session=session,
            tenant_id=current_user.tenant_id,
            name=request.name,
            mobile=request.mobile,
            email=request.email,
            address=request.address,
        )
        session.commit()
        return customer
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error