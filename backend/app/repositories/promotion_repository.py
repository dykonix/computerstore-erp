from datetime import date
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.promotion import Promotion
from app.models.promotion_benefit import PromotionBenefit
from app.models.promotion_group import PromotionGroup
from app.models.promotion_product import PromotionProduct


class PromotionRepository:
    """Data-access operations for tenant-scoped promotions."""

    # ------------------------------------------------------------------
    # Promotions
    # ------------------------------------------------------------------

    @staticmethod
    def list_promotions(
        db: Session,
        tenant_id: int,
        include_inactive: bool = True,
    ) -> list[Promotion]:
        statement = select(Promotion).where(
            Promotion.tenant_id == tenant_id
        )

        if not include_inactive:
            statement = statement.where(Promotion.is_active.is_(True))

        statement = statement.order_by(
            Promotion.valid_from.desc(),
            Promotion.id.desc(),
        )

        return list(db.scalars(statement).all())

    @staticmethod
    def get_promotion(
        db: Session,
        tenant_id: int,
        promotion_id: int,
    ) -> Promotion | None:
        statement = select(Promotion).where(
            Promotion.id == promotion_id,
            Promotion.tenant_id == tenant_id,
        )

        return db.scalars(statement).first()

    @staticmethod
    def create_promotion(
        db: Session,
        tenant_id: int,
        name: str,
        valid_from: date,
        valid_to: date,
        is_active: bool = True,
    ) -> Promotion:
        promotion = Promotion(
            tenant_id=tenant_id,
            name=name,
            valid_from=valid_from,
            valid_to=valid_to,
            is_active=is_active,
        )

        db.add(promotion)
        db.flush()

        return promotion

    @staticmethod
    def update_promotion(
        db: Session,
        tenant_id: int,
        promotion_id: int,
        name: str,
        valid_from: date,
        valid_to: date,
        is_active: bool,
    ) -> Promotion | None:
        promotion = PromotionRepository.get_promotion(
            db=db,
            tenant_id=tenant_id,
            promotion_id=promotion_id,
        )

        if promotion is None:
            return None

        promotion.name = name
        promotion.valid_from = valid_from
        promotion.valid_to = valid_to
        promotion.is_active = is_active

        db.flush()

        return promotion

    @staticmethod
    def set_promotion_status(
        db: Session,
        tenant_id: int,
        promotion_id: int,
        is_active: bool,
    ) -> Promotion | None:
        promotion = PromotionRepository.get_promotion(
            db=db,
            tenant_id=tenant_id,
            promotion_id=promotion_id,
        )

        if promotion is None:
            return None

        promotion.is_active = is_active

        db.flush()

        return promotion

    # ------------------------------------------------------------------
    # Qualifying products
    # ------------------------------------------------------------------

    @staticmethod
    def list_active_for_product(
        db: Session,
        tenant_id: int,
        product_id: int,
        effective_date: date,
    ):
        cashback_amount = (
            select(
                func.coalesce(
                    func.sum(PromotionBenefit.cashback_amount),
                    Decimal("0.00"),
                )
            )
            .select_from(PromotionBenefit)
            .join(
                PromotionGroup,
                PromotionGroup.id == PromotionBenefit.promotion_group_id,
            )
            .where(
                PromotionGroup.promotion_id == Promotion.id,
                PromotionBenefit.benefit_type == "CASHBACK",
                func.upper(PromotionBenefit.payment_mode) == "UPI",
            )
            .correlate(Promotion)
            .scalar_subquery()
        )

        statement = (
            select(Promotion, cashback_amount.label("cashback_amount"))
            .join(
                PromotionProduct,
                PromotionProduct.promotion_id == Promotion.id,
            )
            .join(Product, Product.id == PromotionProduct.product_id)
            .where(
                Promotion.tenant_id == tenant_id,
                Product.tenant_id == tenant_id,
                PromotionProduct.product_id == product_id,
                Promotion.is_active.is_(True),
                Promotion.valid_from <= effective_date,
                Promotion.valid_to >= effective_date,
            )
            .order_by(Promotion.name, Promotion.id)
        )

        return list(db.execute(statement).all())

    @staticmethod
    def get_active_for_product(
        db: Session,
        tenant_id: int,
        promotion_id: int,
        product_id: int,
        effective_date: date,
    ):
        return next(
            (
                (promotion, cashback_amount)
                for promotion, cashback_amount in PromotionRepository.list_active_for_product(
                    db,
                    tenant_id,
                    product_id,
                    effective_date,
                )
                if promotion.id == promotion_id
            ),
            None,
        )

    @staticmethod
    def list_qualifying_product_ids(
        db: Session,
        tenant_id: int,
        promotion_id: int,
    ) -> list[int]:
        """Return product IDs configured as qualifying products.

        Tenant ownership is verified through the promotion.
        """

        promotion_exists = select(Promotion.id).where(
            Promotion.id == promotion_id,
            Promotion.tenant_id == tenant_id,
        )

        if db.scalar(promotion_exists) is None:
            return []

        statement = (
            select(PromotionProduct.product_id)
            .where(PromotionProduct.promotion_id == promotion_id)
            .order_by(PromotionProduct.product_id)
        )

        return list(db.scalars(statement).all())

    @staticmethod
    def add_qualifying_product(
        db: Session,
        tenant_id: int,
        promotion_id: int,
        product_id: int,
    ) -> PromotionProduct | None:
        promotion = PromotionRepository.get_promotion(
            db=db,
            tenant_id=tenant_id,
            promotion_id=promotion_id,
        )

        if promotion is None:
            return None

        existing = db.scalar(
            select(PromotionProduct).where(
                PromotionProduct.promotion_id == promotion_id,
                PromotionProduct.product_id == product_id,
            )
        )

        if existing is not None:
            return existing

        promotion_product = PromotionProduct(
            promotion_id=promotion_id,
            product_id=product_id,
        )

        db.add(promotion_product)
        db.flush()

        return promotion_product

    @staticmethod
    def remove_qualifying_product(
        db: Session,
        tenant_id: int,
        promotion_id: int,
        product_id: int,
    ) -> bool:
        promotion = PromotionRepository.get_promotion(
            db=db,
            tenant_id=tenant_id,
            promotion_id=promotion_id,
        )

        if promotion is None:
            return False

        statement = delete(PromotionProduct).where(
            PromotionProduct.promotion_id == promotion_id,
            PromotionProduct.product_id == product_id,
        )

        result = db.execute(statement)

        return result.rowcount > 0

    @staticmethod
    def replace_qualifying_products(
        db: Session,
        tenant_id: int,
        promotion_id: int,
        product_ids: list[int],
    ) -> bool:
        promotion = PromotionRepository.get_promotion(
            db=db,
            tenant_id=tenant_id,
            promotion_id=promotion_id,
        )

        if promotion is None:
            return False

        db.execute(
            delete(PromotionProduct).where(
                PromotionProduct.promotion_id == promotion_id
            )
        )

        unique_product_ids = list(dict.fromkeys(product_ids))

        for product_id in unique_product_ids:
            db.add(
                PromotionProduct(
                    promotion_id=promotion_id,
                    product_id=product_id,
                )
            )

        db.flush()

        return True

    # ------------------------------------------------------------------
    # Promotion groups
    # ------------------------------------------------------------------

    @staticmethod
    def list_groups(
        db: Session,
        tenant_id: int,
        promotion_id: int,
    ) -> list[PromotionGroup]:
        promotion = PromotionRepository.get_promotion(
            db=db,
            tenant_id=tenant_id,
            promotion_id=promotion_id,
        )

        if promotion is None:
            return []

        statement = (
            select(PromotionGroup)
            .where(PromotionGroup.promotion_id == promotion_id)
            .order_by(PromotionGroup.id)
        )

        return list(db.scalars(statement).all())

    @staticmethod
    def get_group(
        db: Session,
        tenant_id: int,
        group_id: int,
    ) -> PromotionGroup | None:
        statement = (
            select(PromotionGroup)
            .join(
                Promotion,
                Promotion.id == PromotionGroup.promotion_id,
            )
            .where(
                PromotionGroup.id == group_id,
                Promotion.tenant_id == tenant_id,
            )
        )

        return db.scalars(statement).first()

    @staticmethod
    def create_group(
        db: Session,
        tenant_id: int,
        promotion_id: int,
        name: str,
        selection_rule: str,
    ) -> PromotionGroup | None:
        promotion = PromotionRepository.get_promotion(
            db=db,
            tenant_id=tenant_id,
            promotion_id=promotion_id,
        )

        if promotion is None:
            return None

        group = PromotionGroup(
            promotion_id=promotion_id,
            name=name,
            selection_rule=selection_rule,
        )

        db.add(group)
        db.flush()

        return group

    @staticmethod
    def update_group(
        db: Session,
        tenant_id: int,
        group_id: int,
        name: str,
        selection_rule: str,
    ) -> PromotionGroup | None:
        group = PromotionRepository.get_group(
            db=db,
            tenant_id=tenant_id,
            group_id=group_id,
        )

        if group is None:
            return None

        group.name = name
        group.selection_rule = selection_rule

        db.flush()

        return group

    @staticmethod
    def delete_group(
        db: Session,
        tenant_id: int,
        group_id: int,
    ) -> bool:
        group = PromotionRepository.get_group(
            db=db,
            tenant_id=tenant_id,
            group_id=group_id,
        )

        if group is None:
            return False

        db.delete(group)
        db.flush()

        return True

    # ------------------------------------------------------------------
    # Promotion benefits
    # ------------------------------------------------------------------

    @staticmethod
    def list_benefits(
        db: Session,
        tenant_id: int,
        group_id: int,
    ) -> list[PromotionBenefit]:
        group = PromotionRepository.get_group(
            db=db,
            tenant_id=tenant_id,
            group_id=group_id,
        )

        if group is None:
            return []

        statement = (
            select(PromotionBenefit)
            .where(
                PromotionBenefit.promotion_group_id == group_id
            )
            .order_by(PromotionBenefit.id)
        )

        return list(db.scalars(statement).all())

    @staticmethod
    def get_benefit(
        db: Session,
        tenant_id: int,
        benefit_id: int,
    ) -> PromotionBenefit | None:
        statement = (
            select(PromotionBenefit)
            .join(
                PromotionGroup,
                PromotionGroup.id
                == PromotionBenefit.promotion_group_id,
            )
            .join(
                Promotion,
                Promotion.id == PromotionGroup.promotion_id,
            )
            .where(
                PromotionBenefit.id == benefit_id,
                Promotion.tenant_id == tenant_id,
            )
        )

        return db.scalars(statement).first()

    @staticmethod
    def create_product_benefit(
        db: Session,
        tenant_id: int,
        group_id: int,
        product_id: int,
        promotion_price: Decimal,
    ) -> PromotionBenefit | None:
        group = PromotionRepository.get_group(
            db=db,
            tenant_id=tenant_id,
            group_id=group_id,
        )

        if group is None:
            return None

        benefit = PromotionBenefit(
            promotion_group_id=group_id,
            benefit_type="PRODUCT",
            product_id=product_id,
            promotion_price=promotion_price,
        )

        db.add(benefit)
        db.flush()

        return benefit

    @staticmethod
    def create_warranty_benefit(
        db: Session,
        tenant_id: int,
        group_id: int,
        warranty_option_id: int,
        promotion_price: Decimal,
    ) -> PromotionBenefit | None:
        group = PromotionRepository.get_group(
            db=db,
            tenant_id=tenant_id,
            group_id=group_id,
        )

        if group is None:
            return None

        benefit = PromotionBenefit(
            promotion_group_id=group_id,
            benefit_type="WARRANTY",
            warranty_option_id=warranty_option_id,
            promotion_price=promotion_price,
        )

        db.add(benefit)
        db.flush()

        return benefit

    @staticmethod
    def create_cashback_benefit(
        db: Session,
        tenant_id: int,
        group_id: int,
        cashback_amount: Decimal,
        payment_mode: str,
    ) -> PromotionBenefit | None:
        group = PromotionRepository.get_group(
            db=db,
            tenant_id=tenant_id,
            group_id=group_id,
        )

        if group is None:
            return None

        benefit = PromotionBenefit(
            promotion_group_id=group_id,
            benefit_type="CASHBACK",
            cashback_amount=cashback_amount,
            payment_mode=payment_mode,
        )

        db.add(benefit)
        db.flush()

        return benefit

    @staticmethod
    def update_benefit(
        db: Session,
        tenant_id: int,
        benefit_id: int,
        *,
        product_id: int | None = None,
        warranty_option_id: int | None = None,
        promotion_price: Decimal | None = None,
        cashback_amount: Decimal | None = None,
        payment_mode: str | None = None,
    ) -> PromotionBenefit | None:
        benefit = PromotionRepository.get_benefit(
            db=db,
            tenant_id=tenant_id,
            benefit_id=benefit_id,
        )

        if benefit is None:
            return None

        if benefit.benefit_type == "PRODUCT":
            benefit.product_id = product_id
            benefit.warranty_option_id = None
            benefit.promotion_price = promotion_price
            benefit.cashback_amount = None
            benefit.payment_mode = None

        elif benefit.benefit_type == "WARRANTY":
            benefit.product_id = None
            benefit.warranty_option_id = warranty_option_id
            benefit.promotion_price = promotion_price
            benefit.cashback_amount = None
            benefit.payment_mode = None

        elif benefit.benefit_type == "CASHBACK":
            benefit.product_id = None
            benefit.warranty_option_id = None
            benefit.promotion_price = None
            benefit.cashback_amount = cashback_amount
            benefit.payment_mode = payment_mode

        db.flush()

        return benefit

    @staticmethod
    def delete_benefit(
        db: Session,
        tenant_id: int,
        benefit_id: int,
    ) -> bool:
        benefit = PromotionRepository.get_benefit(
            db=db,
            tenant_id=tenant_id,
            benefit_id=benefit_id,
        )

        if benefit is None:
            return False

        db.delete(benefit)
        db.flush()

        return True