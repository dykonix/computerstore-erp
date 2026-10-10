from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.promotion import (
    CashbackBenefitRequest,
    ProductBenefitRequest,
    PromotionBenefitResponse,
    PromotionCreateRequest,
    PromotionGroupCreateRequest,
    PromotionGroupResponse,
    PromotionGroupUpdateRequest,
    PromotionProductResponse,
    ProductPromotionResponse,
    PromotionProductsRequest,
    PromotionResponse,
    PromotionUpdateRequest,
    WarrantyBenefitRequest,
)
from app.services.promotion_service import (
    PromotionService,
    PromotionValidationError,
)

router = APIRouter(prefix="/promotions", tags=["promotions"])


def _service() -> PromotionService:
    return PromotionService()


def _promotion_response(promotion) -> PromotionResponse:
    return PromotionResponse(
        id=promotion.id,
        tenant_id=promotion.tenant_id,
        name=promotion.name,
        valid_from=promotion.valid_from,
        valid_to=promotion.valid_to,
        is_active=promotion.is_active,
    )


def _group_response(group) -> PromotionGroupResponse:
    return PromotionGroupResponse(
        id=group.id,
        promotion_id=group.promotion_id,
        name=group.name,
        selection_rule=group.selection_rule,
    )


def _benefit_response(benefit) -> PromotionBenefitResponse:
    return PromotionBenefitResponse(
        id=benefit.id,
        promotion_group_id=benefit.promotion_group_id,
        benefit_type=benefit.benefit_type,
        product_id=benefit.product_id,
        warranty_option_id=benefit.warranty_option_id,
        promotion_price=benefit.promotion_price,
        cashback_amount=benefit.cashback_amount,
        payment_mode=benefit.payment_mode,
    )


@router.post(
    "",
    response_model=PromotionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_promotion(
    request: PromotionCreateRequest,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: PromotionService = Depends(_service),
) -> PromotionResponse:
    try:
        promotion = service.create_promotion(
            session=session,
            tenant_id=current_user.tenant_id,
            name=request.name,
            valid_from=request.valid_from,
            valid_to=request.valid_to,
        )

        if not request.is_active:
            promotion = service.set_promotion_status(
                session=session,
                tenant_id=current_user.tenant_id,
                promotion_id=promotion.id,
                is_active=False,
            )

        return _promotion_response(promotion)

    except PromotionValidationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("", response_model=list[PromotionResponse])
def list_promotions(
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: PromotionService = Depends(_service),
) -> list[PromotionResponse]:
    promotions = service.repository.list_promotions(
        db=session,
        tenant_id=current_user.tenant_id,
    )

    return [_promotion_response(item) for item in promotions]


@router.get(
    "/products/{product_id}",
    response_model=list[ProductPromotionResponse],
)
def list_active_product_promotions(
    product_id: int,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: PromotionService = Depends(_service),
) -> list[ProductPromotionResponse]:
    promotions = service.repository.list_active_for_product(
        db=session,
        tenant_id=current_user.tenant_id,
        product_id=product_id,
        effective_date=date.today(),
    )

    return [
        ProductPromotionResponse(
            id=promotion.id,
            name=promotion.name,
            cashback_amount=cashback_amount,
        )
        for promotion, cashback_amount in promotions
    ]


@router.get("/{promotion_id}", response_model=PromotionResponse)
def get_promotion(
    promotion_id: int,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: PromotionService = Depends(_service),
) -> PromotionResponse:
    promotion = service.repository.get_promotion(
        db=session,
        tenant_id=current_user.tenant_id,
        promotion_id=promotion_id,
    )

    if promotion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Promotion not found",
        )

    return _promotion_response(promotion)


@router.put("/{promotion_id}", response_model=PromotionResponse)
def update_promotion(
    promotion_id: int,
    request: PromotionUpdateRequest,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: PromotionService = Depends(_service),
) -> PromotionResponse:
    try:
        promotion = service.update_promotion(
            session=session,
            tenant_id=current_user.tenant_id,
            promotion_id=promotion_id,
            name=request.name,
            valid_from=request.valid_from,
            valid_to=request.valid_to,
            is_active=request.is_active,
        )

        return _promotion_response(promotion)

    except PromotionValidationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get(
    "/{promotion_id}/products",
    response_model=list[PromotionProductResponse],
)
def list_qualifying_products(
    promotion_id: int,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: PromotionService = Depends(_service),
) -> list[PromotionProductResponse]:
    promotion = service.repository.get_promotion(
        db=session,
        tenant_id=current_user.tenant_id,
        promotion_id=promotion_id,
    )

    if promotion is None:
        raise HTTPException(status_code=404, detail="Promotion not found")

    product_ids = service.repository.list_qualifying_product_ids(
        db=session,
        tenant_id=current_user.tenant_id,
        promotion_id=promotion_id,
    )

    return [
        PromotionProductResponse(product_id=product_id)
        for product_id in product_ids
    ]


@router.put(
    "/{promotion_id}/products",
    response_model=list[PromotionProductResponse],
)
def replace_qualifying_products(
    promotion_id: int,
    request: PromotionProductsRequest,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: PromotionService = Depends(_service),
) -> list[PromotionProductResponse]:
    try:
        service.replace_qualifying_products(
            session=session,
            tenant_id=current_user.tenant_id,
            promotion_id=promotion_id,
            product_ids=request.product_ids,
        )

        product_ids = service.repository.list_qualifying_product_ids(
            db=session,
            tenant_id=current_user.tenant_id,
            promotion_id=promotion_id,
        )

        return [
            PromotionProductResponse(product_id=product_id)
            for product_id in product_ids
        ]

    except PromotionValidationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post(
    "/{promotion_id}/products",
    response_model=PromotionProductResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_qualifying_product(
    promotion_id: int,
    request: dict,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: PromotionService = Depends(_service),
) -> PromotionProductResponse:
    try:
        service.add_qualifying_product(
            session=session,
            tenant_id=current_user.tenant_id,
            promotion_id=promotion_id,
            product_id=request["product_id"],
        )

        return PromotionProductResponse(
            product_id=request["product_id"],
        )

    except KeyError as error:
        raise HTTPException(
            status_code=422,
            detail="product_id is required",
        ) from error
    except PromotionValidationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get(
    "/{promotion_id}/groups",
    response_model=list[PromotionGroupResponse],
)
def list_groups(
    promotion_id: int,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: PromotionService = Depends(_service),
) -> list[PromotionGroupResponse]:
    promotion = service.repository.get_promotion(
        db=session,
        tenant_id=current_user.tenant_id,
        promotion_id=promotion_id,
    )

    if promotion is None:
        raise HTTPException(status_code=404, detail="Promotion not found")

    groups = service.repository.list_groups(
        db=session,
        tenant_id=current_user.tenant_id,
        promotion_id=promotion_id,
    )

    return [_group_response(group) for group in groups]


@router.post(
    "/{promotion_id}/groups",
    response_model=PromotionGroupResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_group(
    promotion_id: int,
    request: PromotionGroupCreateRequest,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: PromotionService = Depends(_service),
) -> PromotionGroupResponse:
    try:
        group = service.create_group(
            session=session,
            tenant_id=current_user.tenant_id,
            promotion_id=promotion_id,
            name=request.name,
            selection_rule=request.selection_rule,
        )

        return _group_response(group)

    except PromotionValidationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.put(
    "/groups/{group_id}",
    response_model=PromotionGroupResponse,
)
def update_group(
    group_id: int,
    request: PromotionGroupUpdateRequest,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: PromotionService = Depends(_service),
) -> PromotionGroupResponse:
    try:
        group = service.update_group(
            session=session,
            tenant_id=current_user.tenant_id,
            group_id=group_id,
            name=request.name,
            selection_rule=request.selection_rule,
        )

        return _group_response(group)

    except PromotionValidationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.delete(
    "/groups/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_group(
    group_id: int,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: PromotionService = Depends(_service),
) -> None:
    try:
        service.delete_group(
            session=session,
            tenant_id=current_user.tenant_id,
            group_id=group_id,
        )
    except PromotionValidationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get(
    "/groups/{group_id}/benefits",
    response_model=list[PromotionBenefitResponse],
)
def list_benefits(
    group_id: int,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: PromotionService = Depends(_service),
) -> list[PromotionBenefitResponse]:
    group = service.repository.get_group(
        db=session,
        tenant_id=current_user.tenant_id,
        group_id=group_id,
    )

    if group is None:
        raise HTTPException(status_code=404, detail="Promotion group not found")

    benefits = service.repository.list_benefits(
        db=session,
        tenant_id=current_user.tenant_id,
        group_id=group_id,
    )

    return [_benefit_response(benefit) for benefit in benefits]


@router.post(
    "/groups/{group_id}/benefits/product",
    response_model=PromotionBenefitResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_product_benefit(
    group_id: int,
    request: ProductBenefitRequest,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: PromotionService = Depends(_service),
) -> PromotionBenefitResponse:
    try:
        benefit = service.create_product_benefit(
            session=session,
            tenant_id=current_user.tenant_id,
            group_id=group_id,
            product_id=request.product_id,
            promotion_price=request.promotion_price,
        )

        return _benefit_response(benefit)

    except PromotionValidationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post(
    "/groups/{group_id}/benefits/warranty",
    response_model=PromotionBenefitResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_warranty_benefit(
    group_id: int,
    request: WarrantyBenefitRequest,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: PromotionService = Depends(_service),
) -> PromotionBenefitResponse:
    try:
        benefit = service.create_warranty_benefit(
            session=session,
            tenant_id=current_user.tenant_id,
            group_id=group_id,
            warranty_option_id=request.warranty_option_id,
            promotion_price=request.promotion_price,
        )

        return _benefit_response(benefit)

    except PromotionValidationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post(
    "/groups/{group_id}/benefits/cashback",
    response_model=PromotionBenefitResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_cashback_benefit(
    group_id: int,
    request: CashbackBenefitRequest,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: PromotionService = Depends(_service),
) -> PromotionBenefitResponse:
    try:
        benefit = service.create_cashback_benefit(
            session=session,
            tenant_id=current_user.tenant_id,
            group_id=group_id,
            cashback_amount=request.cashback_amount,
            payment_mode=request.payment_mode,
        )

        return _benefit_response(benefit)

    except PromotionValidationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error