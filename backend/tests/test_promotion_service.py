import unittest
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.models.brand import Brand
from app.models.category import Category
from app.models.product import Product
from app.models.tenant import Tenant
from app.models.warranty_option import WarrantyOption
from app.services.promotion_service import (
    PromotionService,
    PromotionValidationError,
)


class PromotionServiceTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        Base.metadata.create_all(cls.engine)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(cls.engine)
        cls.engine.dispose()

    def setUp(self):
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)

        with Session(self.engine) as session:
            tenant = Tenant(name="Tenant One")
            other_tenant = Tenant(name="Tenant Two")

            category = Category(name="Laptops")
            brand = Brand(name="HP")

            session.add_all([
                tenant,
                other_tenant,
                category,
                brand,
            ])

            session.flush()

            product = Product(
                tenant_id=tenant.id,
                category_id=category.id,
                brand_id=brand.id,
                sku="HP-001",
                name="HP Laptop",
                is_active=True,
            )

            other_product = Product(
                tenant_id=other_tenant.id,
                category_id=category.id,
                brand_id=brand.id,
                sku="HP-OTHER",
                name="Other Tenant Laptop",
                is_active=True,
            )

            session.add_all([
                product,
                other_product,
            ])

            # Product IDs are generated only after flush.
            session.flush()

            warranty = WarrantyOption(
                product_id=product.id,
                additional_months=24,
                is_active=True,
            )

            session.add(warranty)
            session.flush()

            self.tenant_id = tenant.id
            self.other_tenant_id = other_tenant.id
            self.product_id = product.id
            self.other_product_id = other_product.id
            self.warranty_id = warranty.id
            session.commit()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def create_promotion(
        self,
        session: Session,
        tenant_id: int | None = None,
    ):
        service = PromotionService()

        return service.create_promotion(
            session=session,
            tenant_id=tenant_id or self.tenant_id,
            name="Festival Offer",
            valid_from=date(2026, 10, 1),
            valid_to=date(2026, 10, 31),
        )

    def create_group(
        self,
        session: Session,
        promotion_id: int,
    ):
        service = PromotionService()

        return service.create_group(
            session=session,
            tenant_id=self.tenant_id,
            promotion_id=promotion_id,
            name="Student Benefit",
            selection_rule="ONE",
        )

    # ------------------------------------------------------------------
    # Promotion validation
    # ------------------------------------------------------------------

    def test_create_promotion(self):
        service = PromotionService()

        with Session(self.engine) as session:
            promotion = service.create_promotion(
                session=session,
                tenant_id=self.tenant_id,
                name="  Festival Offer  ",
                valid_from=date(2026, 10, 1),
                valid_to=date(2026, 10, 31),
            )

            self.assertEqual(
                promotion.name,
                "Festival Offer",
            )

            self.assertEqual(
                promotion.valid_from,
                date(2026, 10, 1),
            )

            self.assertTrue(
                promotion.is_active,
            )

    def test_create_promotion_rejects_blank_name(self):
        service = PromotionService()

        with Session(self.engine) as session:
            with self.assertRaises(PromotionValidationError):
                service.create_promotion(
                    session=session,
                    tenant_id=self.tenant_id,
                    name="   ",
                    valid_from=date(2026, 10, 1),
                    valid_to=date(2026, 10, 31),
                )

    def test_create_promotion_rejects_invalid_dates(self):
        service = PromotionService()

        with Session(self.engine) as session:
            with self.assertRaises(PromotionValidationError):
                service.create_promotion(
                    session=session,
                    tenant_id=self.tenant_id,
                    name="Invalid Dates",
                    valid_from=date(2026, 11, 1),
                    valid_to=date(2026, 10, 31),
                )

    def test_update_promotion_rejects_invalid_dates(self):
        service = PromotionService()

        with Session(self.engine) as session:
            promotion = self.create_promotion(session)

            with self.assertRaises(PromotionValidationError):
                service.update_promotion(
                    session=session,
                    tenant_id=self.tenant_id,
                    promotion_id=promotion.id,
                    name="Updated",
                    valid_from=date(2026, 12, 1),
                    valid_to=date(2026, 11, 30),
                    is_active=True,
                )

    def test_update_promotion_rejects_other_tenant(self):
        service = PromotionService()

        with Session(self.engine) as session:
            promotion = self.create_promotion(session)

            with self.assertRaises(PromotionValidationError):
                service.update_promotion(
                    session=session,
                    tenant_id=self.other_tenant_id,
                    promotion_id=promotion.id,
                    name="Hijacked",
                    valid_from=date(2026, 10, 1),
                    valid_to=date(2026, 10, 31),
                    is_active=True,
                )

    # ------------------------------------------------------------------
    # Qualifying product validation
    # ------------------------------------------------------------------

    def test_add_qualifying_product(self):
        service = PromotionService()

        with Session(self.engine) as session:
            promotion = self.create_promotion(session)

            service.add_qualifying_product(
                session=session,
                tenant_id=self.tenant_id,
                promotion_id=promotion.id,
                product_id=self.product_id,
            )

            product_ids = (
                service.repository.list_qualifying_product_ids(
                    db=session,
                    tenant_id=self.tenant_id,
                    promotion_id=promotion.id,
                )
            )

            self.assertEqual(
                product_ids,
                [self.product_id],
            )

    def test_add_qualifying_product_rejects_duplicate(self):
        service = PromotionService()

        with Session(self.engine) as session:
            promotion = self.create_promotion(session)

            service.add_qualifying_product(
                session=session,
                tenant_id=self.tenant_id,
                promotion_id=promotion.id,
                product_id=self.product_id,
            )

            with self.assertRaises(PromotionValidationError):
                service.add_qualifying_product(
                    session=session,
                    tenant_id=self.tenant_id,
                    promotion_id=promotion.id,
                    product_id=self.product_id,
                )

    def test_add_qualifying_product_rejects_other_tenant_product(self):
        service = PromotionService()

        with Session(self.engine) as session:
            promotion = self.create_promotion(session)

            with self.assertRaises(PromotionValidationError):
                service.add_qualifying_product(
                    session=session,
                    tenant_id=self.tenant_id,
                    promotion_id=promotion.id,
                    product_id=self.other_product_id,
                )

    def test_replace_qualifying_products_removes_duplicates(self):
        service = PromotionService()

        with Session(self.engine) as session:
            promotion = self.create_promotion(session)

            result = service.replace_qualifying_products(
                session=session,
                tenant_id=self.tenant_id,
                promotion_id=promotion.id,
                product_ids=[
                    self.product_id,
                    self.product_id,
                    self.product_id,
                ],
            )

            self.assertTrue(result)

            product_ids = (
                service.repository.list_qualifying_product_ids(
                    db=session,
                    tenant_id=self.tenant_id,
                    promotion_id=promotion.id,
                )
            )

            self.assertEqual(
                product_ids,
                [self.product_id],
            )

    # ------------------------------------------------------------------
    # Group validation
    # ------------------------------------------------------------------

    def test_create_group(self):
        service = PromotionService()

        with Session(self.engine) as session:
            promotion = self.create_promotion(session)

            group = service.create_group(
                session=session,
                tenant_id=self.tenant_id,
                promotion_id=promotion.id,
                name="  Student Benefit  ",
                selection_rule="ONE",
            )

            self.assertEqual(
                group.name,
                "Student Benefit",
            )

            self.assertEqual(
                group.selection_rule,
                "ONE",
            )

    def test_create_group_rejects_invalid_selection_rule(self):
        service = PromotionService()

        with Session(self.engine) as session:
            promotion = self.create_promotion(session)

            with self.assertRaises(PromotionValidationError):
                service.create_group(
                    session=session,
                    tenant_id=self.tenant_id,
                    promotion_id=promotion.id,
                    name="Invalid Group",
                    selection_rule="INVALID",
                )

    def test_create_group_rejects_other_tenant_promotion(self):
        service = PromotionService()

        with Session(self.engine) as session:
            promotion = self.create_promotion(session)

            with self.assertRaises(PromotionValidationError):
                service.create_group(
                    session=session,
                    tenant_id=self.other_tenant_id,
                    promotion_id=promotion.id,
                    name="Other Tenant Group",
                    selection_rule="ONE",
                )

    # ------------------------------------------------------------------
    # Product benefit
    # ------------------------------------------------------------------

    def test_create_product_benefit(self):
        service = PromotionService()

        with Session(self.engine) as session:
            promotion = self.create_promotion(session)

            group = self.create_group(
                session=session,
                promotion_id=promotion.id,
            )

            benefit = service.create_product_benefit(
                session=session,
                tenant_id=self.tenant_id,
                group_id=group.id,
                product_id=self.product_id,
                promotion_price=Decimal("999.00"),
            )

            self.assertEqual(
                benefit.benefit_type,
                "PRODUCT",
            )

            self.assertEqual(
                benefit.product_id,
                self.product_id,
            )

            self.assertEqual(
                benefit.promotion_price,
                Decimal("999.00"),
            )

    def test_product_benefit_rejects_negative_price(self):
        service = PromotionService()

        with Session(self.engine) as session:
            promotion = self.create_promotion(session)

            group = self.create_group(
                session=session,
                promotion_id=promotion.id,
            )

            with self.assertRaises(PromotionValidationError):
                service.create_product_benefit(
                    session=session,
                    tenant_id=self.tenant_id,
                    group_id=group.id,
                    product_id=self.product_id,
                    promotion_price=Decimal("-1.00"),
                )

    def test_product_benefit_rejects_other_tenant_product(self):
        service = PromotionService()

        with Session(self.engine) as session:
            promotion = self.create_promotion(session)

            group = self.create_group(
                session=session,
                promotion_id=promotion.id,
            )

            with self.assertRaises(PromotionValidationError):
                service.create_product_benefit(
                    session=session,
                    tenant_id=self.tenant_id,
                    group_id=group.id,
                    product_id=self.other_product_id,
                    promotion_price=Decimal("100.00"),
                )

    # ------------------------------------------------------------------
    # Warranty benefit
    # ------------------------------------------------------------------

    def test_create_warranty_benefit(self):
        service = PromotionService()

        with Session(self.engine) as session:
            promotion = self.create_promotion(session)

            group = self.create_group(
                session=session,
                promotion_id=promotion.id,
            )

            benefit = service.create_warranty_benefit(
                session=session,
                tenant_id=self.tenant_id,
                group_id=group.id,
                warranty_option_id=self.warranty_id,
                promotion_price=Decimal("499.00"),
            )

            self.assertEqual(
                benefit.benefit_type,
                "WARRANTY",
            )

            self.assertEqual(
                benefit.warranty_option_id,
                self.warranty_id,
            )

    def test_warranty_benefit_rejects_negative_price(self):
        service = PromotionService()

        with Session(self.engine) as session:
            promotion = self.create_promotion(session)

            group = self.create_group(
                session=session,
                promotion_id=promotion.id,
            )

            with self.assertRaises(PromotionValidationError):
                service.create_warranty_benefit(
                    session=session,
                    tenant_id=self.tenant_id,
                    group_id=group.id,
                    warranty_option_id=self.warranty_id,
                    promotion_price=Decimal("-10.00"),
                )

    # ------------------------------------------------------------------
    # Cashback
    # ------------------------------------------------------------------

    def test_create_cashback_benefit(self):
        service = PromotionService()

        with Session(self.engine) as session:
            promotion = self.create_promotion(session)

            group = self.create_group(
                session=session,
                promotion_id=promotion.id,
            )

            benefit = service.create_cashback_benefit(
                session=session,
                tenant_id=self.tenant_id,
                group_id=group.id,
                cashback_amount=Decimal("500.00"),
                payment_mode="upi",
            )

            self.assertEqual(
                benefit.benefit_type,
                "CASHBACK",
            )

            self.assertEqual(
                benefit.cashback_amount,
                Decimal("500.00"),
            )

            self.assertEqual(
                benefit.payment_mode,
                "UPI",
            )

    def test_cashback_rejects_negative_amount(self):
        service = PromotionService()

        with Session(self.engine) as session:
            promotion = self.create_promotion(session)

            group = self.create_group(
                session=session,
                promotion_id=promotion.id,
            )

            with self.assertRaises(PromotionValidationError):
                service.create_cashback_benefit(
                    session=session,
                    tenant_id=self.tenant_id,
                    group_id=group.id,
                    cashback_amount=Decimal("-1.00"),
                    payment_mode="UPI",
                )

    def test_cashback_rejects_invalid_payment_mode(self):
        service = PromotionService()

        with Session(self.engine) as session:
            promotion = self.create_promotion(session)

            group = self.create_group(
                session=session,
                promotion_id=promotion.id,
            )

            with self.assertRaises(PromotionValidationError):
                service.create_cashback_benefit(
                    session=session,
                    tenant_id=self.tenant_id,
                    group_id=group.id,
                    cashback_amount=Decimal("500.00"),
                    payment_mode="CASH",
                )

    # ------------------------------------------------------------------
    # Benefit type safety
    # ------------------------------------------------------------------

    def test_update_product_benefit_rejects_wrong_benefit_type(self):
        service = PromotionService()

        with Session(self.engine) as session:
            promotion = self.create_promotion(session)

            group = self.create_group(
                session=session,
                promotion_id=promotion.id,
            )

            benefit = service.create_cashback_benefit(
                session=session,
                tenant_id=self.tenant_id,
                group_id=group.id,
                cashback_amount=Decimal("100.00"),
                payment_mode="UPI",
            )

            with self.assertRaises(PromotionValidationError):
                service.update_product_benefit(
                    session=session,
                    tenant_id=self.tenant_id,
                    benefit_id=benefit.id,
                    product_id=self.product_id,
                    promotion_price=Decimal("50.00"),
                )

    # ------------------------------------------------------------------
    # Group deletion rule
    # ------------------------------------------------------------------

    def test_group_with_benefits_cannot_be_deleted(self):
        service = PromotionService()

        with Session(self.engine) as session:
            promotion = self.create_promotion(session)

            group = self.create_group(
                session=session,
                promotion_id=promotion.id,
            )

            service.create_product_benefit(
                session=session,
                tenant_id=self.tenant_id,
                group_id=group.id,
                product_id=self.product_id,
                promotion_price=Decimal("100.00"),
            )

            with self.assertRaises(PromotionValidationError):
                service.delete_group(
                    session=session,
                    tenant_id=self.tenant_id,
                    group_id=group.id,
                )

    def test_empty_group_can_be_deleted(self):
        service = PromotionService()

        with Session(self.engine) as session:
            promotion = self.create_promotion(session)

            group = self.create_group(
                session=session,
                promotion_id=promotion.id,
            )

            service.delete_group(
                session=session,
                tenant_id=self.tenant_id,
                group_id=group.id,
            )

            loaded = service.repository.get_group(
                db=session,
                tenant_id=self.tenant_id,
                group_id=group.id,
            )

            self.assertIsNone(loaded)

    # ------------------------------------------------------------------
    # Tenant isolation
    # ------------------------------------------------------------------

    def test_other_tenant_cannot_access_group(self):
        service = PromotionService()

        with Session(self.engine) as session:
            promotion = self.create_promotion(session)

            group = self.create_group(
                session=session,
                promotion_id=promotion.id,
            )

            with self.assertRaises(PromotionValidationError):
                service.create_product_benefit(
                    session=session,
                    tenant_id=self.other_tenant_id,
                    group_id=group.id,
                    product_id=self.product_id,
                    promotion_price=Decimal("100.00"),
                )


if __name__ == "__main__":
    unittest.main()