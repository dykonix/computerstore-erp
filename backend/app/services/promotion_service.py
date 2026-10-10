from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.promotion_benefit import PromotionBenefit
from app.models.warranty_option import WarrantyOption
from app.repositories.promotion_repository import PromotionRepository


class PromotionValidationError(ValueError):
    """Raised when a promotion operation violates a V1 business rule."""


class PromotionService:
    """Application and business rules for V1 promotions."""

    VALID_SELECTION_RULES = {
        "REQUIRED",
        "ONE",
        "ALL",
        "OPTIONAL",
    }

    VALID_BENEFIT_TYPES = {
        "PRODUCT",
        "WARRANTY",
        "CASHBACK",
    }

    VALID_CASHBACK_PAYMENT_MODES = {
        "UPI",
    }

    def __init__(self) -> None:
        self.repository = PromotionRepository()

    # ------------------------------------------------------------------
    # Internal validation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_name(name: str) -> str:
        normalized_name = name.strip()

        if not normalized_name:
            raise PromotionValidationError(
                "Promotion name is required"
            )

        return normalized_name

    @staticmethod
    def _validate_dates(
        valid_from: date,
        valid_to: date,
    ) -> None:
        if valid_to < valid_from:
            raise PromotionValidationError(
                "Promotion end date cannot be before start date"
            )

    @staticmethod
    def _validate_selection_rule(
        selection_rule: str,
    ) -> None:
        if selection_rule not in PromotionService.VALID_SELECTION_RULES:
            raise PromotionValidationError(
                f"Invalid promotion selection rule: {selection_rule}"
            )

    @staticmethod
    def _validate_positive_or_zero_amount(
        amount: Decimal,
        field_name: str,
    ) -> None:
        if amount < Decimal("0"):
            raise PromotionValidationError(
                f"{field_name} cannot be negative"
            )

    @staticmethod
    def _get_product_for_tenant(
        session: Session,
        tenant_id: int,
        product_id: int,
    ) -> Product:
        product = session.scalar(
            select(Product).where(
                Product.id == product_id,
                Product.tenant_id == tenant_id,
            )
        )

        if product is None:
            raise PromotionValidationError(
                "Product does not belong to the current tenant"
            )

        return product

    @staticmethod
    def _get_warranty_for_tenant(
        session: Session,
        tenant_id: int,
        warranty_option_id: int,
    ) -> WarrantyOption:
        statement = (
            select(WarrantyOption)
            .join(
                Product,
                Product.id == WarrantyOption.product_id,
            )
            .where(
                WarrantyOption.id == warranty_option_id,
                Product.tenant_id == tenant_id,
            )
        )

        warranty = session.scalar(statement)

        if warranty is None:
            raise PromotionValidationError(
                "Warranty option does not belong to the current tenant"
            )

        return warranty

    # ------------------------------------------------------------------
    # Promotion lifecycle
    # ------------------------------------------------------------------

    def create_promotion(
        self,
        session: Session,
        tenant_id: int,
        name: str,
        valid_from: date,
        valid_to: date,
        is_active: bool = True,
    ):
        normalized_name = self._validate_name(name)

        self._validate_dates(
            valid_from=valid_from,
            valid_to=valid_to,
        )

        return self.repository.create_promotion(
            db=session,
            tenant_id=tenant_id,
            name=normalized_name,
            valid_from=valid_from,
            valid_to=valid_to,
            is_active=is_active,
        )

    def update_promotion(
        self,
        session: Session,
        tenant_id: int,
        promotion_id: int,
        name: str,
        valid_from: date,
        valid_to: date,
        is_active: bool,
    ):
        normalized_name = self._validate_name(name)

        self._validate_dates(
            valid_from=valid_from,
            valid_to=valid_to,
        )

        promotion = self.repository.update_promotion(
            db=session,
            tenant_id=tenant_id,
            promotion_id=promotion_id,
            name=normalized_name,
            valid_from=valid_from,
            valid_to=valid_to,
            is_active=is_active,
        )

        if promotion is None:
            raise PromotionValidationError(
                "Promotion not found"
            )

        return promotion

    def activate_promotion(
        self,
        session: Session,
        tenant_id: int,
        promotion_id: int,
    ):
        promotion = self.repository.set_promotion_status(
            db=session,
            tenant_id=tenant_id,
            promotion_id=promotion_id,
            is_active=True,
        )

        if promotion is None:
            raise PromotionValidationError(
                "Promotion not found"
            )

        return promotion

    def deactivate_promotion(
        self,
        session: Session,
        tenant_id: int,
        promotion_id: int,
    ):
        promotion = self.repository.set_promotion_status(
            db=session,
            tenant_id=tenant_id,
            promotion_id=promotion_id,
            is_active=False,
        )

        if promotion is None:
            raise PromotionValidationError(
                "Promotion not found"
            )

        return promotion

    # ------------------------------------------------------------------
    # Qualifying products
    # ------------------------------------------------------------------

    def add_qualifying_product(
        self,
        session: Session,
        tenant_id: int,
        promotion_id: int,
        product_id: int,
    ):
        promotion = self.repository.get_promotion(
            db=session,
            tenant_id=tenant_id,
            promotion_id=promotion_id,
        )

        if promotion is None:
            raise PromotionValidationError(
                "Promotion not found"
            )

        self._get_product_for_tenant(
            session=session,
            tenant_id=tenant_id,
            product_id=product_id,
        )

        existing_product_ids = (
            self.repository.list_qualifying_product_ids(
                db=session,
                tenant_id=tenant_id,
                promotion_id=promotion_id,
            )
        )

        if product_id in existing_product_ids:
            raise PromotionValidationError(
                "Product is already a qualifying product"
            )

        return self.repository.add_qualifying_product(
            db=session,
            tenant_id=tenant_id,
            promotion_id=promotion_id,
            product_id=product_id,
        )

    def replace_qualifying_products(
        self,
        session: Session,
        tenant_id: int,
        promotion_id: int,
        product_ids: list[int],
    ):
        promotion = self.repository.get_promotion(
            db=session,
            tenant_id=tenant_id,
            promotion_id=promotion_id,
        )

        if promotion is None:
            raise PromotionValidationError(
                "Promotion not found"
            )

        unique_product_ids = list(dict.fromkeys(product_ids))

        for product_id in unique_product_ids:
            self._get_product_for_tenant(
                session=session,
                tenant_id=tenant_id,
                product_id=product_id,
            )

        return self.repository.replace_qualifying_products(
            db=session,
            tenant_id=tenant_id,
            promotion_id=promotion_id,
            product_ids=unique_product_ids,
        )

    def remove_qualifying_product(
        self,
        session: Session,
        tenant_id: int,
        promotion_id: int,
        product_id: int,
    ) -> None:
        promotion = self.repository.get_promotion(
            db=session,
            tenant_id=tenant_id,
            promotion_id=promotion_id,
        )

        if promotion is None:
            raise PromotionValidationError(
                "Promotion not found"
            )

        removed = self.repository.remove_qualifying_product(
            db=session,
            tenant_id=tenant_id,
            promotion_id=promotion_id,
            product_id=product_id,
        )

        if not removed:
            raise PromotionValidationError(
                "Qualifying product was not found"
            )

    # ------------------------------------------------------------------
    # Groups
    # ------------------------------------------------------------------

    def create_group(
        self,
        session: Session,
        tenant_id: int,
        promotion_id: int,
        name: str,
        selection_rule: str,
    ):
        promotion = self.repository.get_promotion(
            db=session,
            tenant_id=tenant_id,
            promotion_id=promotion_id,
        )

        if promotion is None:
            raise PromotionValidationError(
                "Promotion not found"
            )

        normalized_name = self._validate_name(name)

        self._validate_selection_rule(selection_rule)

        return self.repository.create_group(
            db=session,
            tenant_id=tenant_id,
            promotion_id=promotion_id,
            name=normalized_name,
            selection_rule=selection_rule,
        )

    def update_group(
        self,
        session: Session,
        tenant_id: int,
        group_id: int,
        name: str,
        selection_rule: str,
    ):
        normalized_name = self._validate_name(name)

        self._validate_selection_rule(selection_rule)

        group = self.repository.update_group(
            db=session,
            tenant_id=tenant_id,
            group_id=group_id,
            name=normalized_name,
            selection_rule=selection_rule,
        )

        if group is None:
            raise PromotionValidationError(
                "Promotion group not found"
            )

        return group

    def delete_group(
        self,
        session: Session,
        tenant_id: int,
        group_id: int,
    ) -> None:
        benefits = self.repository.list_benefits(
            db=session,
            tenant_id=tenant_id,
            group_id=group_id,
        )

        if benefits:
            raise PromotionValidationError(
                "Promotion group cannot be deleted while it contains benefits"
            )

        deleted = self.repository.delete_group(
            db=session,
            tenant_id=tenant_id,
            group_id=group_id,
        )

        if not deleted:
            raise PromotionValidationError(
                "Promotion group not found"
            )

    # ------------------------------------------------------------------
    # Benefits
    # ------------------------------------------------------------------

    def create_product_benefit(
        self,
        session: Session,
        tenant_id: int,
        group_id: int,
        product_id: int,
        promotion_price: Decimal,
    ):
        self._get_group_or_raise(
            session=session,
            tenant_id=tenant_id,
            group_id=group_id,
        )

        self._get_product_for_tenant(
            session=session,
            tenant_id=tenant_id,
            product_id=product_id,
        )

        self._validate_positive_or_zero_amount(
            amount=promotion_price,
            field_name="Promotion price",
        )

        return self.repository.create_product_benefit(
            db=session,
            tenant_id=tenant_id,
            group_id=group_id,
            product_id=product_id,
            promotion_price=promotion_price,
        )

    def create_warranty_benefit(
        self,
        session: Session,
        tenant_id: int,
        group_id: int,
        warranty_option_id: int,
        promotion_price: Decimal,
    ):
        self._get_group_or_raise(
            session=session,
            tenant_id=tenant_id,
            group_id=group_id,
        )

        self._get_warranty_for_tenant(
            session=session,
            tenant_id=tenant_id,
            warranty_option_id=warranty_option_id,
        )

        self._validate_positive_or_zero_amount(
            amount=promotion_price,
            field_name="Promotion price",
        )

        return self.repository.create_warranty_benefit(
            db=session,
            tenant_id=tenant_id,
            group_id=group_id,
            warranty_option_id=warranty_option_id,
            promotion_price=promotion_price,
        )

    def create_cashback_benefit(
        self,
        session: Session,
        tenant_id: int,
        group_id: int,
        cashback_amount: Decimal,
        payment_mode: str,
    ):
        self._get_group_or_raise(
            session=session,
            tenant_id=tenant_id,
            group_id=group_id,
        )

        self._validate_positive_or_zero_amount(
            amount=cashback_amount,
            field_name="Cashback amount",
        )

        normalized_payment_mode = payment_mode.strip().upper()

        if normalized_payment_mode not in self.VALID_CASHBACK_PAYMENT_MODES:
            raise PromotionValidationError(
                "Invalid cashback payment mode"
            )

        return self.repository.create_cashback_benefit(
            db=session,
            tenant_id=tenant_id,
            group_id=group_id,
            cashback_amount=cashback_amount,
            payment_mode=normalized_payment_mode,
        )

    def update_product_benefit(
        self,
        session: Session,
        tenant_id: int,
        benefit_id: int,
        product_id: int,
        promotion_price: Decimal,
    ):
        benefit = self._get_benefit_or_raise(
            session=session,
            tenant_id=tenant_id,
            benefit_id=benefit_id,
        )

        if benefit.benefit_type != "PRODUCT":
            raise PromotionValidationError(
                "Benefit is not a product benefit"
            )

        self._get_product_for_tenant(
            session=session,
            tenant_id=tenant_id,
            product_id=product_id,
        )

        self._validate_positive_or_zero_amount(
            amount=promotion_price,
            field_name="Promotion price",
        )

        return self.repository.update_benefit(
            db=session,
            tenant_id=tenant_id,
            benefit_id=benefit_id,
            product_id=product_id,
            promotion_price=promotion_price,
        )

    def update_warranty_benefit(
        self,
        session: Session,
        tenant_id: int,
        benefit_id: int,
        warranty_option_id: int,
        promotion_price: Decimal,
    ):
        benefit = self._get_benefit_or_raise(
            session=session,
            tenant_id=tenant_id,
            benefit_id=benefit_id,
        )

        if benefit.benefit_type != "WARRANTY":
            raise PromotionValidationError(
                "Benefit is not a warranty benefit"
            )

        self._get_warranty_for_tenant(
            session=session,
            tenant_id=tenant_id,
            warranty_option_id=warranty_option_id,
        )

        self._validate_positive_or_zero_amount(
            amount=promotion_price,
            field_name="Promotion price",
        )

        return self.repository.update_benefit(
            db=session,
            tenant_id=tenant_id,
            benefit_id=benefit_id,
            warranty_option_id=warranty_option_id,
            promotion_price=promotion_price,
        )

    def update_cashback_benefit(
        self,
        session: Session,
        tenant_id: int,
        benefit_id: int,
        cashback_amount: Decimal,
        payment_mode: str,
    ):
        benefit = self._get_benefit_or_raise(
            session=session,
            tenant_id=tenant_id,
            benefit_id=benefit_id,
        )

        if benefit.benefit_type != "CASHBACK":
            raise PromotionValidationError(
                "Benefit is not a cashback benefit"
            )

        self._validate_positive_or_zero_amount(
            amount=cashback_amount,
            field_name="Cashback amount",
        )

        normalized_payment_mode = payment_mode.strip().upper()

        if normalized_payment_mode not in self.VALID_CASHBACK_PAYMENT_MODES:
            raise PromotionValidationError(
                "Invalid cashback payment mode"
            )

        return self.repository.update_benefit(
            db=session,
            tenant_id=tenant_id,
            benefit_id=benefit_id,
            cashback_amount=cashback_amount,
            payment_mode=normalized_payment_mode,
        )

    def delete_benefit(
        self,
        session: Session,
        tenant_id: int,
        benefit_id: int,
    ) -> None:
        deleted = self.repository.delete_benefit(
            db=session,
            tenant_id=tenant_id,
            benefit_id=benefit_id,
        )

        if not deleted:
            raise PromotionValidationError(
                "Promotion benefit not found"
            )

    # ------------------------------------------------------------------
    # Internal entity access helpers
    # ------------------------------------------------------------------

    def _get_group_or_raise(
        self,
        session: Session,
        tenant_id: int,
        group_id: int,
    ):
        group = self.repository.get_group(
            db=session,
            tenant_id=tenant_id,
            group_id=group_id,
        )

        if group is None:
            raise PromotionValidationError(
                "Promotion group not found"
            )

        return group

    def _get_benefit_or_raise(
        self,
        session: Session,
        tenant_id: int,
        benefit_id: int,
    ) -> PromotionBenefit:
        benefit = self.repository.get_benefit(
            db=session,
            tenant_id=tenant_id,
            benefit_id=benefit_id,
        )

        if benefit is None:
            raise PromotionValidationError(
                "Promotion benefit not found"
            )

        return benefit