from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.category import (
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
)
from app.services.category_service import (
    CategoryNotFoundError,
    CategoryService,
    CategoryValidationError,
)

router = APIRouter(prefix="/categories", tags=["categories"])


def _service() -> CategoryService:
    return CategoryService()


@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_category(
    request: CategoryCreate,
    session: Session = Depends(get_db),
    service: CategoryService = Depends(_service),
) -> CategoryResponse:
    try:
        category = service.create(session, request)
        return CategoryResponse.model_validate(category)
    except CategoryValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error


@router.get("", response_model=list[CategoryResponse])
def list_categories(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_active: bool | None = Query(None),
    session: Session = Depends(get_db),
    service: CategoryService = Depends(_service),
) -> list[CategoryResponse]:
    offset = (page - 1) * page_size

    categories, _ = service.list(
        session,
        offset,
        page_size,
        is_active,
    )

    return [
        CategoryResponse.model_validate(category)
        for category in categories
    ]


@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
)
def get_category(
    category_id: int,
    session: Session = Depends(get_db),
    service: CategoryService = Depends(_service),
) -> CategoryResponse:
    try:
        category = service.get_by_id(
            session,
            category_id,
        )

        return CategoryResponse.model_validate(category)

    except CategoryNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error


@router.put(
    "/{category_id}",
    response_model=CategoryResponse,
)
def update_category(
    category_id: int,
    request: CategoryUpdate,
    session: Session = Depends(get_db),
    service: CategoryService = Depends(_service),
) -> CategoryResponse:
    try:
        category = service.update(
            session,
            category_id,
            request,
        )

        return CategoryResponse.model_validate(category)

    except CategoryNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    except CategoryValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error


@router.patch(
    "/{category_id}/status",
    response_model=CategoryResponse,
)
def set_category_status(
    category_id: int,
    is_active: bool,
    session: Session = Depends(get_db),
    service: CategoryService = Depends(_service),
) -> CategoryResponse:
    try:
        category = service.set_status(
            session,
            category_id,
            is_active,
        )

        return CategoryResponse.model_validate(category)

    except CategoryNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error