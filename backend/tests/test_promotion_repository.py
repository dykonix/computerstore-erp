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
from app.models.promotion import Promotion
from app.models.promotion_benefit import PromotionBenefit
from app.models.promotion_group import PromotionGroup
from app.models.promotion_product import PromotionProduct
from app.models.tenant import Tenant
from app.models.warranty_option import WarrantyOption
from app.repositories.promotion_repository import PromotionRepository


class PromotionRepositoryTestCase(unittest.TestCase):

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
        self.db = Session(self.engine)

        self.tenant_1 = Tenant(
            name="Tenant One",
        )

        self.tenant_2 = Tenant(
            name="Tenant Two",
        )

        self.db.add_all([
            self.tenant_1,
            self.tenant_2,
        ])
        self.db.flush()

        self.category = Category(
            name="Laptops",
        )

        self.brand = Brand(
            name="HP",
        )

        self.db.add_all([
            self.category,
            self.brand,
        ])
        self.db.flush()

        self.product_1 = Product(
            tenant_id=self.tenant_1.id,
            category_id=self.category.id,
            brand_id=self.brand.id,
            sku="HP-001",
            name="HP Laptop 1",
            default_warranty_months=12,
            requires_serial_number=False,
        )

        self.product_2 = Product(
            tenant_id=self.tenant_1.id,
            category_id=self.category.id,
            brand_id=self.brand.id,
            sku="HP-002",
            name="HP Laptop 2",
            default_warranty_months=12,
            requires_serial_number=False,
        )

        self.db.add_all([
            self.product_1,
            self.product_2,
        ])
        self.db.flush()

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    # ------------------------------------------------------------------
    # Promotion tests
    # ------------------------------------------------------------------

    def test_create_and_get_promotion(self):
        promotion = PromotionRepository.create_promotion(
            db=self.db,
            tenant_id=self.tenant_1.id,
            name="Festival Offer",
            valid_from=date(2026, 10, 1),
            valid_to=date(2026, 10, 31),
        )

        self.assertIsNotNone(promotion.id)
        self.assertEqual(promotion.name, "Festival Offer")
        self.assertTrue(promotion.is_active)

        loaded = PromotionRepository.get_promotion(
            db=self.db,
            tenant_id=self.tenant_1.id,
            promotion_id=promotion.id,
        )

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.id, promotion.id)
        self.assertEqual(loaded.name, "Festival Offer")

    def test_get_promotion_is_tenant_scoped(self):
        promotion = PromotionRepository.create_promotion(
            db=self.db,
            tenant_id=self.tenant_1.id,
            name="Tenant One Offer",
            valid_from=date(2026, 10, 1),
            valid_to=date(2026, 10, 31),
        )

        loaded = PromotionRepository.get_promotion(
            db=self.db,
            tenant_id=self.tenant_2.id,
            promotion_id=promotion.id,
        )

        self.assertIsNone(loaded)

    def test_list_promotions_can_exclude_inactive(self):
        active = PromotionRepository.create_promotion(
            db=self.db,
            tenant_id=self.tenant_1.id,
            name="Active Offer",
            valid_from=date(2026, 10, 1),
            valid_to=date(2026, 10, 31),
            is_active=True,
        )

        inactive = PromotionRepository.create_promotion(
            db=self.db,
            tenant_id=self.tenant_1.id,
            name="Inactive Offer",
            valid_from=date(2026, 10, 1),
            valid_to=date(2026, 10, 31),
            is_active=False,
        )

        all_promotions = PromotionRepository.list_promotions(
            db=self.db,
            tenant_id=self.tenant_1.id,
        )

        active_promotions = PromotionRepository.list_promotions(
            db=self.db,
            tenant_id=self.tenant_1.id,
            include_inactive=False,
        )

        all_ids = {promotion.id for promotion in all_promotions}
        active_ids = {promotion.id for promotion in active_promotions}

        self.assertIn(active.id, all_ids)
        self.assertIn(inactive.id, all_ids)

        self.assertIn(active.id, active_ids)
        self.assertNotIn(inactive.id, active_ids)

    def test_update_promotion(self):
        promotion = PromotionRepository.create_promotion(
            db=self.db,
            tenant_id=self.tenant_1.id,
            name="Original Offer",
            valid_from=date(2026, 10, 1),
            valid_to=date(2026, 10, 31),
        )

        updated = PromotionRepository.update_promotion(
            db=self.db,
            tenant_id=self.tenant_1.id,
            promotion_id=promotion.id,
            name="Updated Offer",
            valid_from=date(2026, 10, 5),
            valid_to=date(2026, 11, 5),
            is_active=False,
        )

        self.assertIsNotNone(updated)
        self.assertEqual(updated.name, "Updated Offer")
        self.assertEqual(updated.valid_from, date(2026, 10, 5))
        self.assertEqual(updated.valid_to, date(2026, 11, 5))
        self.assertFalse(updated.is_active)

    def test_set_promotion_status(self):
        promotion = PromotionRepository.create_promotion(
            db=self.db,
            tenant_id=self.tenant_1.id,
            name="Status Test",
            valid_from=date(2026, 10, 1),
            valid_to=date(2026, 10, 31),
            is_active=True,
        )

        updated = PromotionRepository.set_promotion_status(
            db=self.db,
            tenant_id=self.tenant_1.id,
            promotion_id=promotion.id,
            is_active=False,
        )

        self.assertFalse(updated.is_active)

    # ------------------------------------------------------------------
    # Qualifying product tests
    # ------------------------------------------------------------------

    def test_add_and_list_qualifying_products(self):
        promotion = PromotionRepository.create_promotion(
            db=self.db,
            tenant_id=self.tenant_1.id,
            name="Laptop Offer",
            valid_from=date(2026, 10, 1),
            valid_to=date(2026, 10, 31),
        )

        PromotionRepository.add_qualifying_product(
            db=self.db,
            tenant_id=self.tenant_1.id,
            promotion_id=promotion.id,
            product_id=self.product_1.id,
        )

        PromotionRepository.add_qualifying_product(
            db=self.db,
            tenant_id=self.tenant_1.id,
            promotion_id=promotion.id,
            product_id=self.product_2.id,
        )

        product_ids = PromotionRepository.list_qualifying_product_ids(
            db=self.db,
            tenant_id=self.tenant_1.id,
            promotion_id=promotion.id,
        )

        self.assertEqual(
            product_ids,
            [self.product_1.id, self.product_2.id],
        )

    def test_duplicate_qualifying_product_is_not_added_twice(self):
        promotion = PromotionRepository.create_promotion(
            db=self.db,
            tenant_id=self.tenant_1.id,
            name="Duplicate Test",
            valid_from=date(2026, 10, 1),
            valid_to=date(2026, 10, 31),
        )

        first = PromotionRepository.add_qualifying_product(
            db=self.db,
            tenant_id=self.tenant_1.id,
            promotion_id=promotion.id,
            product_id=self.product_1.id,
        )

        second = PromotionRepository.add_qualifying_product(
            db=self.db,
            tenant_id=self.tenant_1.id,
            promotion_id=promotion.id,
            product_id=self.product_1.id,
        )

        self.assertEqual(first.promotion_id, second.promotion_id)
        self.assertEqual(first.product_id, second.product_id)

        product_ids = PromotionRepository.list_qualifying_product_ids(
            db=self.db,
            tenant_id=self.tenant_1.id,
            promotion_id=promotion.id,
        )

        self.assertEqual(product_ids, [self.product_1.id])

    def test_replace_qualifying_products(self):
        promotion = PromotionRepository.create_promotion(
            db=self.db,
            tenant_id=self.tenant_1.id,
            name="Replace Test",
            valid_from=date(2026, 10, 1),
            valid_to=date(2026, 10, 31),
        )

        PromotionRepository.replace_qualifying_products(
            db=self.db,
            tenant_id=self.tenant_1.id,
            promotion_id=promotion.id,
            product_ids=[self.product_1.id],
        )

        PromotionRepository.replace_qualifying_products(
            db=self.db,
            tenant_id=self.tenant_1.id,
            promotion_id=promotion.id,
            product_ids=[self.product_2.id],
        )

        product_ids = PromotionRepository.list_qualifying_product_ids(
            db=self.db,
            tenant_id=self.tenant_1.id,
            promotion_id=promotion.id,
        )

        self.assertEqual(product_ids, [self.product_2.id])

    def test_remove_qualifying_product(self):
        promotion = PromotionRepository.create_promotion(
            db=self.db,
            tenant_id=self.tenant_1.id,
            name="Remove Test",
            valid_from=date(2026, 10, 1),
            valid_to=date(2026, 10, 31),
        )

        PromotionRepository.add_qualifying_product(
            db=self.db,
            tenant_id=self.tenant_1.id,
            promotion_id=promotion.id,
            product_id=self.product_1.id,
        )

        removed = PromotionRepository.remove_qualifying_product(
            db=self.db,
            tenant_id=self.tenant_1.id,
            promotion_id=promotion.id,
            product_id=self.product_1.id,
        )

        self.assertTrue(removed)

        product_ids = PromotionRepository.list_qualifying_product_ids(
            db=self.db,
            tenant_id=self.tenant_1.id,
            promotion_id=promotion.id,
        )

        self.assertEqual(product_ids, [])

    # ------------------------------------------------------------------
    # Promotion group tests
    # ------------------------------------------------------------------

    def test_create_and_list_groups(self):
        promotion = PromotionRepository.create_promotion(
            db=self.db,
            tenant_id=self.tenant_1.id,
            name="Group Test",
            valid_from=date(2026, 10, 1),
            valid_to=date(2026, 10, 31),
        )

        group = PromotionRepository.create_group(
            db=self.db,
            tenant_id=self.tenant_1.id,
            promotion_id=promotion.id,
            name="Student Benefit",
            selection_rule="ONE",
        )

        groups = PromotionRepository.list_groups(
            db=self.db,
            tenant_id=self.tenant_1.id,
            promotion_id=promotion.id,
        )

        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].id, group.id)
        self.assertEqual(groups[0].name, "Student Benefit")
        self.assertEqual(groups[0].selection_rule, "ONE")

    def test_group_access_is_tenant_scoped(self):
        promotion = PromotionRepository.create_promotion(
            db=self.db,
            tenant_id=self.tenant_1.id,
            name="Tenant Group Test",
            valid_from=date(2026, 10, 1),
            valid_to=date(2026, 10, 31),
        )

        group = PromotionRepository.create_group(
            db=self.db,
            tenant_id=self.tenant_1.id,
            promotion_id=promotion.id,
            name="Private Group",
            selection_rule="REQUIRED",
        )

        loaded = PromotionRepository.get_group(
            db=self.db,
            tenant_id=self.tenant_2.id,
            group_id=group.id,
        )

        self.assertIsNone(loaded)

    def test_update_group(self):
        promotion = PromotionRepository.create_promotion(
            db=self.db,
            tenant_id=self.tenant_1.id,
            name="Group Update Test",
            valid_from=date(2026, 10, 1),
            valid_to=date(2026, 10, 31),
        )

        group = PromotionRepository.create_group(
            db=self.db,
            tenant_id=self.tenant_1.id,
            promotion_id=promotion.id,
            name="Original",
            selection_rule="ONE",
        )

        updated = PromotionRepository.update_group(
            db=self.db,
            tenant_id=self.tenant_1.id,
            group_id=group.id,
            name="Updated",
            selection_rule="ALL",
        )

        self.assertEqual(updated.name, "Updated")
        self.assertEqual(updated.selection_rule, "ALL")

    # ------------------------------------------------------------------
    # Benefit tests
    # ------------------------------------------------------------------

    def test_create_product_benefit(self):
        promotion = PromotionRepository.create_promotion(
            db=self.db,
            tenant_id=self.tenant_1.id,
            name="Product Benefit",
            valid_from=date(2026, 10, 1),
            valid_to=date(2026, 10, 31),
        )

        group = PromotionRepository.create_group(
            db=self.db,
            tenant_id=self.tenant_1.id,
            promotion_id=promotion.id,
            name="Free Product",
            selection_rule="ONE",
        )

        benefit = PromotionRepository.create_product_benefit(
            db=self.db,
            tenant_id=self.tenant_1.id,
            group_id=group.id,
            product_id=self.product_2.id,
            promotion_price=Decimal("999.00"),
        )

        self.assertIsNotNone(benefit)
        self.assertEqual(benefit.benefit_type, "PRODUCT")
        self.assertEqual(benefit.product_id, self.product_2.id)
        self.assertEqual(
            benefit.promotion_price,
            Decimal("999.00"),
        )

    def test_create_warranty_benefit(self):
        promotion = PromotionRepository.create_promotion(
            db=self.db,
            tenant_id=self.tenant_1.id,
            name="Warranty Benefit",
            valid_from=date(2026, 10, 1),
            valid_to=date(2026, 10, 31),
        )

        group = PromotionRepository.create_group(
            db=self.db,
            tenant_id=self.tenant_1.id,
            promotion_id=promotion.id,
            name="Warranty",
            selection_rule="OPTIONAL",
        )

        warranty = WarrantyOption(
            product_id=self.product_1.id,
            additional_months=24,
            is_active=True,
        )

        self.db.add(warranty)
        self.db.flush()

        benefit = PromotionRepository.create_warranty_benefit(
            db=self.db,
            tenant_id=self.tenant_1.id,
            group_id=group.id,
            warranty_option_id=warranty.id,
            promotion_price=Decimal("499.00"),
        )

        self.assertIsNotNone(benefit)
        self.assertEqual(benefit.benefit_type, "WARRANTY")
        self.assertEqual(
            benefit.warranty_option_id,
            warranty.id,
        )
        self.assertEqual(
            benefit.promotion_price,
            Decimal("499.00"),
        )

    def test_create_cashback_benefit(self):
        promotion = PromotionRepository.create_promotion(
            db=self.db,
            tenant_id=self.tenant_1.id,
            name="UPI Cashback",
            valid_from=date(2026, 10, 1),
            valid_to=date(2026, 10, 31),
        )

        group = PromotionRepository.create_group(
            db=self.db,
            tenant_id=self.tenant_1.id,
            promotion_id=promotion.id,
            name="Cashback",
            selection_rule="ONE",
        )

        benefit = PromotionRepository.create_cashback_benefit(
            db=self.db,
            tenant_id=self.tenant_1.id,
            group_id=group.id,
            cashback_amount=Decimal("500.00"),
            payment_mode="UPI",
        )

        self.assertIsNotNone(benefit)
        self.assertEqual(benefit.benefit_type, "CASHBACK")
        self.assertEqual(
            benefit.cashback_amount,
            Decimal("500.00"),
        )
        self.assertEqual(
            benefit.payment_mode,
            "UPI",
        )

    def test_list_benefits(self):
        promotion = PromotionRepository.create_promotion(
            db=self.db,
            tenant_id=self.tenant_1.id,
            name="Benefits Test",
            valid_from=date(2026, 10, 1),
            valid_to=date(2026, 10, 31),
        )

        group = PromotionRepository.create_group(
            db=self.db,
            tenant_id=self.tenant_1.id,
            promotion_id=promotion.id,
            name="Benefits",
            selection_rule="ALL",
        )

        PromotionRepository.create_product_benefit(
            db=self.db,
            tenant_id=self.tenant_1.id,
            group_id=group.id,
            product_id=self.product_2.id,
            promotion_price=Decimal("100.00"),
        )

        PromotionRepository.create_cashback_benefit(
            db=self.db,
            tenant_id=self.tenant_1.id,
            group_id=group.id,
            cashback_amount=Decimal("200.00"),
            payment_mode="UPI",
        )

        benefits = PromotionRepository.list_benefits(
            db=self.db,
            tenant_id=self.tenant_1.id,
            group_id=group.id,
        )

        self.assertEqual(len(benefits), 2)
        self.assertEqual(
            {benefit.benefit_type for benefit in benefits},
            {"PRODUCT", "CASHBACK"},
        )

    def test_benefit_access_is_tenant_scoped(self):
        promotion = PromotionRepository.create_promotion(
            db=self.db,
            tenant_id=self.tenant_1.id,
            name="Private Benefit",
            valid_from=date(2026, 10, 1),
            valid_to=date(2026, 10, 31),
        )

        group = PromotionRepository.create_group(
            db=self.db,
            tenant_id=self.tenant_1.id,
            promotion_id=promotion.id,
            name="Private Group",
            selection_rule="ONE",
        )

        benefit = PromotionRepository.create_product_benefit(
            db=self.db,
            tenant_id=self.tenant_1.id,
            group_id=group.id,
            product_id=self.product_2.id,
            promotion_price=Decimal("100.00"),
        )

        loaded = PromotionRepository.get_benefit(
            db=self.db,
            tenant_id=self.tenant_2.id,
            benefit_id=benefit.id,
        )

        self.assertIsNone(loaded)

    def test_update_product_benefit(self):
        promotion = PromotionRepository.create_promotion(
            db=self.db,
            tenant_id=self.tenant_1.id,
            name="Benefit Update",
            valid_from=date(2026, 10, 1),
            valid_to=date(2026, 10, 31),
        )

        group = PromotionRepository.create_group(
            db=self.db,
            tenant_id=self.tenant_1.id,
            promotion_id=promotion.id,
            name="Product Benefit",
            selection_rule="ONE",
        )

        benefit = PromotionRepository.create_product_benefit(
            db=self.db,
            tenant_id=self.tenant_1.id,
            group_id=group.id,
            product_id=self.product_1.id,
            promotion_price=Decimal("100.00"),
        )

        updated = PromotionRepository.update_benefit(
            db=self.db,
            tenant_id=self.tenant_1.id,
            benefit_id=benefit.id,
            product_id=self.product_2.id,
            promotion_price=Decimal("250.00"),
        )

        self.assertEqual(updated.product_id, self.product_2.id)
        self.assertEqual(
            updated.promotion_price,
            Decimal("250.00"),
        )
        self.assertIsNone(updated.warranty_option_id)
        self.assertIsNone(updated.cashback_amount)
        self.assertIsNone(updated.payment_mode)

    def test_delete_benefit(self):
        promotion = PromotionRepository.create_promotion(
            db=self.db,
            tenant_id=self.tenant_1.id,
            name="Benefit Delete",
            valid_from=date(2026, 10, 1),
            valid_to=date(2026, 10, 31),
        )

        group = PromotionRepository.create_group(
            db=self.db,
            tenant_id=self.tenant_1.id,
            promotion_id=promotion.id,
            name="Delete Group",
            selection_rule="ONE",
        )

        benefit = PromotionRepository.create_cashback_benefit(
            db=self.db,
            tenant_id=self.tenant_1.id,
            group_id=group.id,
            cashback_amount=Decimal("100.00"),
            payment_mode="UPI",
        )

        deleted = PromotionRepository.delete_benefit(
            db=self.db,
            tenant_id=self.tenant_1.id,
            benefit_id=benefit.id,
        )

        self.assertTrue(deleted)

        loaded = PromotionRepository.get_benefit(
            db=self.db,
            tenant_id=self.tenant_1.id,
            benefit_id=benefit.id,
        )

        self.assertIsNone(loaded)


if __name__ == "__main__":
    unittest.main()