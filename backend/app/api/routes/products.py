from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_tenant_id
from app.database.session import get_db
from app.schemas.product import (
    AttributeOptionSummary,
    AttributeSummary,
    BrandSummary,
    CategoryAttributeSummary,
    CategorySummary,
    ProductAttributeValueResponse,
    ProductCreate,
    ProductFormDataResponse,
    ProductListItem,
    ProductListResponse,
    ProductResponse,
)
from app.services.product_service import (
    ProductNotFoundError,
    ProductService,
    ProductValidationError,
)

router = APIRouter(prefix="/products", tags=["products"])


def _service() -> ProductService:
    return ProductService()


@router.get("/form-data", response_model=ProductFormDataResponse)
def get_product_form_data(
    session: Session = Depends(get_db), service: ProductService = Depends(_service)
) -> ProductFormDataResponse:
    repository = service.repository
    return ProductFormDataResponse(
        categories=[
            CategorySummary(id=item.id, name=item.name)
            for item in repository.get_active_categories(session)
        ],
        brands=[
            BrandSummary(id=item.id, name=item.name)
            for item in repository.get_active_brands(session)
        ],
        attributes=[
            AttributeSummary(
                id=item.id, name=item.name, data_type=item.data_type, unit=item.unit
            )
            for item in repository.get_active_attributes(session)
        ],
        attribute_options=[
            AttributeOptionSummary(
                id=item.id,
                attribute_id=item.attribute_id,
                value=item.value,
                display_order=item.display_order,
            )
            for item in repository.get_active_attribute_options(session)
        ],
        category_attributes=[
            CategoryAttributeSummary(
                category_id=item.category_id,
                attribute_id=item.attribute_id,
                is_required=item.is_required,
                display_order=item.display_order,
            )
            for item in repository.get_category_attributes(session)
        ],
    )


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    request: ProductCreate,
    session: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    service: ProductService = Depends(_service),
) -> ProductResponse:
    try:
        product = service.create_product(session, tenant_id, request)
        row, values = service.get_product(session, tenant_id, product.id)
        return _product_response(row, values)
    except ProductValidationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("", response_model=ProductListResponse)
def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    service: ProductService = Depends(_service),
) -> ProductListResponse:
    rows, total = service.list_products(session, tenant_id, page, page_size)
    return ProductListResponse(
        items=[
            ProductListItem(
                id=product.id,
                sku=product.sku,
                name=product.name,
                category=CategorySummary(id=product.category_id, name=category_name),
                brand=BrandSummary(id=product.brand_id, name=brand_name),
                is_active=product.is_active,
            )
            for product, category_name, brand_name in rows
        ],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    request: ProductCreate,
    session: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    service: ProductService = Depends(_service),
) -> ProductResponse:
    try:
        product = service.update_product(session, tenant_id, product_id, request)
        row, values = service.get_product(session, tenant_id, product.id)
        return _product_response(row, values)
    except ProductNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ProductValidationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    session: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    service: ProductService = Depends(_service),
) -> ProductResponse:
    try:
        row, values = service.get_product(session, tenant_id, product_id)
        return _product_response(row, values)
    except ProductNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


def _product_response(row, values) -> ProductResponse:
    product, category_name, brand_name = row
    return ProductResponse(
        id=product.id,
        sku=product.sku,
        name=product.name,
        description=product.description,
        category=CategorySummary(id=product.category_id, name=category_name),
        brand=BrandSummary(id=product.brand_id, name=brand_name),
        is_active=product.is_active,
        attributes=[
            ProductAttributeValueResponse(
                id=value.id,
                attribute_id=value.attribute_id,
                attribute_name=attribute.name,
                data_type=attribute.data_type,
                unit=attribute.unit,
                attribute_option_id=value.attribute_option_id,
                attribute_option_value=option.value if option else None,
                text_value=value.text_value,
                number_value=value.number_value,
                decimal_value=value.decimal_value,
            )
            for value, attribute, option in values
        ],
    )