from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.services.authorization_service import (
    AuthorizationService,
    PermissionDeniedError,
)


router = APIRouter(
    prefix="/stores",
    tags=["stores"],
)


class StoreResponse(BaseModel):
    id: int
    name: str
    address: str | None
    is_active: bool


def _service() -> AuthorizationService:
    return AuthorizationService()


@router.get(
    "",
    response_model=list[StoreResponse],
)
def list_allowed_stores(
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        stores = _service().list_allowed_stores(
            session=session,
            user=current_user,
            permission_code="sell",
        )

        return [
            StoreResponse(
                id=store.id,
                name=store.name,
                address=store.address,
                is_active=store.is_active,
            )
            for store in stores
        ]

    except PermissionDeniedError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied",
        ) from error