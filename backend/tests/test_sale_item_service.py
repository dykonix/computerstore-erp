import unittest

from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models.brand import Brand
from app.models.category import Category
from app.models.employee import Employee
from app.models.employee_store import EmployeeStore
from app.models.inventory import Inventory
from app.models.permission import Permission
from app.models.product import Product
from app.models.product_price import ProductPrice
from app.models.promotion import Promotion
from app.models.promotion_benefit import PromotionBenefit
from app.models.promotion_group import PromotionGroup
from app.models.promotion_product import PromotionProduct
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.store import Store
from app.models.tenant import Tenant
from app.models.user import User
from app.models.user_role import UserRole
from app.services.sale_service import SaleService
from app.schemas.sale import SaleItemCreate
from pydantic import ValidationError


class SaleItemServiceTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(cls.engine)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(cls.engine)
        cls.engine.dispose()

    def setUp(self):
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)

        with Session(self.engine) as session:
            tenant = Tenant(name="Tenant")

            category = Category(
                name="Laptop",
                gst_rate=Decimal("18.00"),
            )

            brand = Brand(name="HP")

            session.add_all([
                tenant,
                category,
                brand,
            ])
            session.flush()

            employee = Employee(
                tenant_id=tenant.id,
                email="sales@example.com",
                name="Sales Employee",
                is_active=True,
            )

            store = Store(
                tenant_id=tenant.id,
                name="Main Store",
                is_active=True,
            )

            product = Product(
                tenant_id=tenant.id,
                category_id=category.id,
                brand_id=brand.id,
                sku="HP-1",
                name="HP Laptop",
                is_active=True,
            )

            permission = Permission(
                code="sell",
                description="Sell products",
            )

            role = Role(
                tenant_id=tenant.id,
                name="Sales",
                is_active=True,
            )

            session.add_all([
                employee,
                store,
                product,
                permission,
                role,
            ])
            session.flush()

            user = User(
                tenant_id=tenant.id,
                username="sales-user",
                email="sales.user@example.com",
                mobile="9999999999",
                password_hash="test-hash",
                employee_id=employee.id,
                is_active=True,
            )

            # Flush the user first so the database-generated
            # user.id is available before creating UserRole.
            session.add(user)
            session.flush()

            employee_store = EmployeeStore(
                employee_id=employee.id,
                store_id=store.id,
            )

            user_role = UserRole(
                user_id=user.id,
                role_id=role.id,
            )

            role_permission = RolePermission(
                role_id=role.id,
                permission_id=permission.id,
                scope="assigned_stores",
            )

            session.add_all([
                employee_store,
                user_role,
                role_permission,
            ])
            session.flush()

            sale = Sale(
                tenant_id=tenant.id,
                store_id=store.id,
                employee_id=employee.id,
                status="DRAFT",
                subtotal=Decimal("0.00"),
                invoice_discount=Decimal("0.00"),
                taxable_amount=Decimal("0.00"),
                gst_amount=Decimal("0.00"),
                total_amount=Decimal("0.00"),
            )

            session.add(sale)
            session.add(
                Inventory(
                    tenant_id=tenant.id,
                    product_id=product.id,
                    store_id=store.id,
                    quantity=5,
                    reserved_quantity=1,
                )
            )
            session.flush()

            price = ProductPrice(
                product_id=product.id,
                cost_price=Decimal("40000.00"),
                sale_price=Decimal("50000.00"),
                minimum_sale_price=Decimal("45000.00"),
                valid_from=date.today(),
                valid_to=None,
            )

            session.add(price)
            session.commit()

            self.tenant_id = tenant.id
            self.employee_id = employee.id
            self.store_id = store.id
            self.product_id = product.id
            self.user_id = user.id
            self.sale_id = sale.id

    def get_user(self):
        with Session(self.engine) as session:
            return session.get(User, self.user_id)

    def test_add_item_uses_current_price_and_calculates_gst(self):
        with Session(self.engine) as session:
            user = session.get(User, self.user_id)

            item = SaleService().add_sale_item(
                session=session,
                current_user=user,
                sale_id=self.sale_id,
                product_id=self.product_id,
                quantity=2,
            )

            self.assertEqual(
                item.configured_unit_price,
                Decimal("50000.00"),
            )

            self.assertEqual(
                item.actual_unit_price,
                Decimal("50000.00"),
            )

            self.assertEqual(
                item.cost_price,
                Decimal("40000.00"),
            )

            self.assertEqual(
                item.gst_rate,
                Decimal("18.00"),
            )

            self.assertEqual(
                item.gst_amount,
                Decimal("15254.24"),
            )

            self.assertEqual(
                item.line_total,
                Decimal("100000.00"),
            )

    def test_negotiated_price_creates_discount(self):
        with Session(self.engine) as session:
            user = session.get(User, self.user_id)

            item = SaleService().add_sale_item(
                session=session,
                current_user=user,
                sale_id=self.sale_id,
                product_id=self.product_id,
                quantity=2,
                actual_unit_price=Decimal("48000.00"),
            )

            self.assertEqual(
                item.configured_unit_price,
                Decimal("50000.00"),
            )

            self.assertEqual(
                item.actual_unit_price,
                Decimal("48000.00"),
            )

            self.assertEqual(
                item.discount_amount,
                Decimal("4000.00"),
            )

            self.assertEqual(
                item.line_total,
                Decimal("96000.00"),
            )

            self.assertEqual(
                item.gst_amount,
                Decimal("14644.07"),
            )

    def test_sale_totals_are_recalculated_after_adding_item(self):
        with Session(self.engine) as session:
            user = session.get(User, self.user_id)

            SaleService().add_sale_item(
                session=session,
                current_user=user,
                sale_id=self.sale_id,
                product_id=self.product_id,
                quantity=2,
                actual_unit_price=Decimal("48000.00"),
            )

            sale = session.get(Sale, self.sale_id)

            self.assertEqual(
                sale.subtotal,
                Decimal("96000.00"),
            )

            self.assertEqual(
                sale.taxable_amount,
                Decimal("81355.93"),
            )

            self.assertEqual(
                sale.gst_amount,
                Decimal("14644.07"),
            )

            self.assertEqual(
                sale.total_amount,
                Decimal("96000.00"),
            )

            self.assertEqual(
                sale.payable_amount,
                Decimal("96000.00"),
            )

    def test_selected_upi_cashback_promotion_reduces_payable(self):
        with Session(self.engine) as session:
            promotion = Promotion(
                tenant_id=self.tenant_id,
                name="UPI Cashback",
                valid_from=date.today(),
                valid_to=date.today(),
                is_active=True,
            )
            session.add(promotion)
            session.flush()

            group = PromotionGroup(
                promotion_id=promotion.id,
                name="Cashback",
                selection_rule="OPTIONAL",
            )
            session.add_all([
                group,
                PromotionProduct(
                    promotion_id=promotion.id,
                    product_id=self.product_id,
                ),
            ])
            session.flush()
            session.add(
                PromotionBenefit(
                    promotion_group_id=group.id,
                    benefit_type="CASHBACK",
                    cashback_amount=Decimal("500.00"),
                    payment_mode="UPI",
                )
            )
            session.flush()

            user = session.get(User, self.user_id)
            item = SaleService().add_sale_item(
                session=session,
                current_user=user,
                sale_id=self.sale_id,
                product_id=self.product_id,
                quantity=2,
                promotion_id=promotion.id,
            )
            sale = session.get(Sale, self.sale_id)

            self.assertEqual(item.promotion_name, "UPI Cashback")
            self.assertEqual(item.promotion_cashback_amount, Decimal("500.00"))
            self.assertEqual(item.cost_price, Decimal("40000.00"))
            self.assertEqual(sale.total_amount, Decimal("100000.00"))
            self.assertEqual(sale.cashback_amount, Decimal("500.00"))
            self.assertEqual(sale.payable_amount, Decimal("99500.00"))

    def test_selected_product_benefits_and_cashback_create_distinct_sale_lines(self):
        with Session(self.engine) as session:
            promotion = Promotion(
                tenant_id=self.tenant_id,
                name="Student Offer",
                valid_from=date.today(),
                valid_to=date.today(),
                is_active=True,
            )
            session.add(promotion)
            session.flush()
            group = PromotionGroup(
                promotion_id=promotion.id,
                name="Student Benefits",
                selection_rule="REQUIRED",
                group_requirement="REQUIRED",
                benefit_selection_rule="ALL",
            )
            source_product = session.get(Product, self.product_id)
            gift_products = [
                Product(
                    tenant_id=self.tenant_id,
                    category_id=source_product.category_id,
                    brand_id=source_product.brand_id,
                    sku=f"GIFT-{index}",
                    name=name,
                )
                for index, name in enumerate(
                    ("Trolley Bag", "Titan Glass", "AI Fiesta"), start=1
                )
            ]
            session.add_all([group, *gift_products])
            session.add(
                PromotionProduct(
                    promotion_id=promotion.id,
                    product_id=self.product_id,
                )
            )
            session.flush()
            product_benefits = [
                PromotionBenefit(
                    promotion_group_id=group.id,
                    benefit_type="PRODUCT",
                    product_id=product.id,
                    promotion_price=price,
                )
                for product, price in zip(
                    gift_products,
                    (Decimal("699.00"), Decimal("499.00"), Decimal("0.00")),
                )
            ]
            cashback_benefit = PromotionBenefit(
                promotion_group_id=group.id,
                benefit_type="CASHBACK",
                cashback_amount=Decimal("2000.00"),
                payment_mode="UPI",
            )
            session.add_all([*product_benefits, cashback_benefit])
            session.flush()

            user = session.get(User, self.user_id)
            source_item = SaleService().add_sale_item(
                session=session,
                current_user=user,
                sale_id=self.sale_id,
                product_id=self.product_id,
                quantity=1,
                promotion_id=promotion.id,
                promotion_benefit_ids=[
                    *(benefit.id for benefit in product_benefits),
                    cashback_benefit.id,
                ],
            )
            sale = session.get(Sale, self.sale_id)
            sale_items = SaleService().sale_repository.list_sale_items(
                session, self.sale_id
            )

            gift_items = [item for item in sale_items if item.is_promotion_benefit]
            self.assertEqual(len(gift_items), 3)
            self.assertEqual(
                {item.promotion_benefit_name for item in gift_items},
                {"Trolley Bag", "Titan Glass", "AI Fiesta"},
            )
            self.assertEqual(
                {item.actual_unit_price for item in gift_items},
                {Decimal("699.00"), Decimal("499.00"), Decimal("0.00")},
            )
            self.assertEqual(
                {item.promotion_source_sale_item_id for item in gift_items},
                {source_item.id},
            )
            self.assertTrue(
                next(item for item in gift_items if item.actual_unit_price == 0).is_free_product
            )
            self.assertEqual(sale.cashback_amount, Decimal("2000.00"))
            self.assertEqual(sale.total_amount, Decimal("51198.00"))
            self.assertEqual(sale.payable_amount, Decimal("49198.00"))

    def test_two_units_can_select_different_benefits_without_duplication(self):
        with Session(self.engine) as session:
            promotion = Promotion(
                tenant_id=self.tenant_id,
                name="Unit Choice",
                valid_from=date.today(),
                valid_to=date.today(),
                is_active=True,
            )
            session.add(promotion)
            session.flush()
            group = PromotionGroup(
                promotion_id=promotion.id,
                name="Choose one per unit",
                selection_rule="OPTIONAL",
                group_requirement="OPTIONAL",
                benefit_selection_rule="ONE",
            )
            cashback_group = PromotionGroup(
                promotion_id=promotion.id,
                name="Optional cashback",
                selection_rule="OPTIONAL",
                group_requirement="OPTIONAL",
                benefit_selection_rule="ANY",
            )
            source_product = session.get(Product, self.product_id)
            trolley = Product(
                tenant_id=self.tenant_id,
                category_id=source_product.category_id,
                brand_id=source_product.brand_id,
                sku="GIFT-TROLLEY",
                name="Trolley Bag",
            )
            glasses = Product(
                tenant_id=self.tenant_id,
                category_id=source_product.category_id,
                brand_id=source_product.brand_id,
                sku="GIFT-GLASSES",
                name="AI Glasses",
            )
            session.add_all([group, cashback_group, trolley, glasses])
            session.add(PromotionProduct(promotion_id=promotion.id, product_id=self.product_id))
            session.flush()
            trolley_benefit = PromotionBenefit(
                promotion_group_id=group.id,
                benefit_type="PRODUCT",
                product_id=trolley.id,
                promotion_price=Decimal("100.00"),
            )
            glasses_benefit = PromotionBenefit(
                promotion_group_id=group.id,
                benefit_type="PRODUCT",
                product_id=glasses.id,
                promotion_price=Decimal("200.00"),
            )
            cashback_benefit = PromotionBenefit(
                promotion_group_id=cashback_group.id,
                benefit_type="CASHBACK",
                cashback_amount=Decimal("500.00"),
                payment_mode="UPI",
            )
            session.add_all([trolley_benefit, glasses_benefit, cashback_benefit])
            session.flush()
            user = session.get(User, self.user_id)
            SaleService().add_sale_item(
                session=session,
                current_user=user,
                sale_id=self.sale_id,
                product_id=self.product_id,
                quantity=2,
                promotion_id=promotion.id,
                promotion_benefit_ids_by_unit=[
                    [trolley_benefit.id, cashback_benefit.id],
                    [glasses_benefit.id],
                ],
                promotion_benefit_sources_by_unit=[
                    {trolley_benefit.id: "MANUFACTURER"},
                    {glasses_benefit.id: "MANUFACTURER"},
                ],
            )
            sale_items = SaleService().sale_repository.list_sale_items(
                session, self.sale_id
            )
            qualifying_items = [item for item in sale_items if not item.is_promotion_benefit]
            benefit_items = [item for item in sale_items if item.is_promotion_benefit]

            self.assertEqual(len(qualifying_items), 2)
            self.assertEqual([item.quantity for item in qualifying_items], [1, 1])
            self.assertEqual(len(benefit_items), 2)
            self.assertEqual(
                {item.promotion_benefit_id: item.promotion_source_sale_item_id for item in benefit_items},
                {
                    trolley_benefit.id: qualifying_items[0].id,
                    glasses_benefit.id: qualifying_items[1].id,
                },
            )
            self.assertEqual(
                {item.promotion_benefit_id for item in benefit_items},
                {trolley_benefit.id, glasses_benefit.id},
            )
            self.assertEqual(
                sum((item.promotion_cashback_amount for item in qualifying_items), Decimal("0.00")),
                Decimal("500.00"),
            )
            self.assertEqual(
                [item.promotion_cashback_amount for item in qualifying_items],
                [Decimal("500.00"), Decimal("0.00")],
            )
            sale = session.get(Sale, self.sale_id)
            self.assertEqual(sale.cashback_amount, Decimal("500.00"))
            self.assertEqual(sale.payable_amount, sale.total_amount - Decimal("500.00"))

    def test_quantity_two_without_promotion_is_accepted(self):
        request = SaleItemCreate(product_id=self.product_id, quantity=2)
        with Session(self.engine) as session:
            user = session.get(User, self.user_id)
            item = SaleService().add_sale_item(
                session=session,
                current_user=user,
                sale_id=self.sale_id,
                product_id=request.product_id,
                quantity=request.quantity,
            )
            self.assertEqual(item.quantity, 2)
            self.assertFalse(item.is_promotion_benefit)

    def test_sources_only_allowed_for_selected_benefits(self):
        valid = SaleItemCreate(
            product_id=self.product_id,
            quantity=2,
            promotion_id=1,
            promotion_benefit_ids_by_unit=[[10], [11]],
            promotion_benefit_sources_by_unit=[{10: "STORE"}, {11: "MANUFACTURER"}],
        )
        self.assertEqual(valid.promotion_benefit_sources_by_unit[0], {10: "STORE"})

        no_sources = SaleItemCreate(
            product_id=self.product_id,
            quantity=2,
            promotion_id=1,
            promotion_benefit_ids_by_unit=[[10], []],
            promotion_benefit_sources_by_unit=[{10: "STORE"}, {}],
        )
        self.assertEqual(no_sources.promotion_benefit_sources_by_unit[1], {})

        with self.assertRaisesRegex(ValidationError, "only be set for selected"):
            SaleItemCreate(
                product_id=self.product_id,
                quantity=2,
                promotion_id=1,
                promotion_benefit_ids_by_unit=[[10], []],
                promotion_benefit_sources_by_unit=[{10: "STORE"}, {11: "STORE"}],
            )

        with self.assertRaises(ValidationError):
            SaleItemCreate(
                product_id=self.product_id,
                quantity=1,
                promotion_id=1,
                promotion_benefit_ids_by_unit=[[10]],
                promotion_benefit_sources_by_unit=[{10: "WAREHOUSE"}],
            )

    def test_quantity_two_keeps_selected_sources_and_skips_unselected_benefit(self):
        with Session(self.engine) as session:
            promotion = Promotion(
                tenant_id=self.tenant_id,
                name="Per Unit Sources",
                valid_from=date.today(),
                valid_to=date.today(),
                is_active=True,
            )
            session.add(promotion)
            session.flush()
            group = PromotionGroup(
                promotion_id=promotion.id,
                name="Gifts",
                selection_rule="OPTIONAL",
                group_requirement="OPTIONAL",
                benefit_selection_rule="ANY",
            )
            source_product = session.get(Product, self.product_id)
            gifts = [
                Product(
                    tenant_id=self.tenant_id,
                    category_id=source_product.category_id,
                    brand_id=source_product.brand_id,
                    sku=f"SRC-{name}",
                    name=name,
                )
                for name in ("Store Gift", "Shipped Gift", "Unselected Gift")
            ]
            session.add_all([group, *gifts])
            session.add(PromotionProduct(promotion_id=promotion.id, product_id=self.product_id))
            session.flush()
            session.add(
                Inventory(
                    tenant_id=self.tenant_id,
                    product_id=gifts[0].id,
                    store_id=session.get(Sale, self.sale_id).store_id,
                    quantity=5,
                    reserved_quantity=0,
                )
            )
            benefits = [
                PromotionBenefit(
                    promotion_group_id=group.id,
                    benefit_type="PRODUCT",
                    product_id=gift.id,
                    promotion_price=Decimal("0.00"),
                )
                for gift in gifts
            ]
            session.add_all(benefits)
            session.flush()
            store_benefit, shipped_benefit, unselected_benefit = benefits

            user = session.get(User, self.user_id)
            SaleService().add_sale_item(
                session=session,
                current_user=user,
                sale_id=self.sale_id,
                product_id=self.product_id,
                quantity=2,
                promotion_id=promotion.id,
                promotion_benefit_ids_by_unit=[[store_benefit.id], [shipped_benefit.id]],
                promotion_benefit_sources_by_unit=[
                    {store_benefit.id: "STORE"},
                    {shipped_benefit.id: "MANUFACTURER"},
                ],
            )
            sale_items = SaleService().sale_repository.list_sale_items(
                session, self.sale_id
            )
            benefit_items = {
                item.promotion_benefit_id: item
                for item in sale_items
                if item.is_promotion_benefit
            }
            self.assertEqual(
                set(benefit_items), {store_benefit.id, shipped_benefit.id}
            )
            self.assertEqual(
                benefit_items[store_benefit.id].promotion_benefit_source, "STORE"
            )
            self.assertEqual(
                benefit_items[shipped_benefit.id].promotion_benefit_source,
                "MANUFACTURER",
            )
            self.assertNotIn(unselected_benefit.id, benefit_items)

    def test_service_rejects_source_for_unselected_benefit(self):
        with Session(self.engine) as session:
            promotion = Promotion(
                tenant_id=self.tenant_id,
                name="Reject Source",
                valid_from=date.today(),
                valid_to=date.today(),
                is_active=True,
            )
            session.add(promotion)
            session.flush()
            group = PromotionGroup(
                promotion_id=promotion.id,
                name="Gifts",
                selection_rule="OPTIONAL",
                group_requirement="OPTIONAL",
                benefit_selection_rule="ANY",
            )
            source_product = session.get(Product, self.product_id)
            gift = Product(
                tenant_id=self.tenant_id,
                category_id=source_product.category_id,
                brand_id=source_product.brand_id,
                sku="REJ-GIFT",
                name="Gift",
            )
            session.add_all([group, gift])
            session.add(PromotionProduct(promotion_id=promotion.id, product_id=self.product_id))
            session.flush()
            benefit = PromotionBenefit(
                promotion_group_id=group.id,
                benefit_type="PRODUCT",
                product_id=gift.id,
                promotion_price=Decimal("0.00"),
            )
            session.add(benefit)
            session.flush()
            user = session.get(User, self.user_id)
            with self.assertRaisesRegex(ValueError, "unselected product benefit"):
                SaleService().add_sale_item(
                    session=session,
                    current_user=user,
                    sale_id=self.sale_id,
                    product_id=self.product_id,
                    quantity=1,
                    promotion_id=promotion.id,
                    promotion_benefit_ids_by_unit=[[]],
                    promotion_benefit_sources_by_unit=[{benefit.id: "STORE"}],
                )

    def test_inclusive_gst_extracts_tax_and_preserves_total(self):
        with Session(self.engine) as session:
            category = session.get(Category, 1)
            category.gst_rate = Decimal("10.00")
            price = session.scalar(
                select(ProductPrice).where(ProductPrice.product_id == self.product_id)
            )
            price.sale_price = Decimal("1000.00")
            price.minimum_sale_price = Decimal("900.00")
            user = session.get(User, self.user_id)
            item = SaleService().add_sale_item(
                session=session,
                current_user=user,
                sale_id=self.sale_id,
                product_id=self.product_id,
                quantity=1,
            )
            sale = session.get(Sale, self.sale_id)

            self.assertEqual(item.line_total, Decimal("1000.00"))
            self.assertEqual(item.gst_amount, Decimal("90.91"))
            self.assertEqual(sale.taxable_amount, Decimal("909.09"))
            self.assertEqual(sale.total_amount, Decimal("1000.00"))
            self.assertEqual(sale.taxable_amount + sale.gst_amount, sale.total_amount)

    def test_missing_gst_configuration_is_rejected(self):
        with Session(self.engine) as session:
            session.get(Category, 1).gst_rate = None
            user = session.get(User, self.user_id)
            with self.assertRaisesRegex(ValueError, "GST rate is not configured"):
                SaleService().add_sale_item(
                    session=session,
                    current_user=user,
                    sale_id=self.sale_id,
                    product_id=self.product_id,
                    quantity=1,
                )

    def test_explicit_zero_gst_rate_remains_zero_rated(self):
        with Session(self.engine) as session:
            session.get(Category, 1).gst_rate = Decimal("0.00")
            price = session.scalar(
                select(ProductPrice).where(ProductPrice.product_id == self.product_id)
            )
            price.sale_price = Decimal("1000.00")
            price.minimum_sale_price = Decimal("900.00")
            user = session.get(User, self.user_id)
            item = SaleService().add_sale_item(
                session=session,
                current_user=user,
                sale_id=self.sale_id,
                product_id=self.product_id,
                quantity=1,
            )
            sale = session.get(Sale, self.sale_id)
            self.assertEqual(item.gst_amount, Decimal("0.00"))
            self.assertEqual(sale.taxable_amount, Decimal("1000.00"))
            self.assertEqual(sale.total_amount, Decimal("1000.00"))

    def test_sale_item_rejects_duplicate_benefit_ids(self):
        with self.assertRaises(ValidationError):
            SaleItemCreate(
                product_id=self.product_id,
                quantity=1,
                promotion_benefit_ids=[5, 5],
            )

    def test_missing_current_price_is_rejected(self):
        with Session(self.engine) as session:
            user = session.get(User, self.user_id)

            session.query(ProductPrice).delete()
            session.flush()

            with self.assertRaises(ValueError) as context:
                SaleService().add_sale_item(
                    session=session,
                    current_user=user,
                    sale_id=self.sale_id,
                    product_id=self.product_id,
                    quantity=1,
                )

            self.assertEqual(
                str(context.exception),
                "No active price found for product",
            )

    def test_quantity_cannot_exceed_selected_store_availability(self):
        with Session(self.engine) as session:
            user = session.get(User, self.user_id)

            with self.assertRaises(ValueError) as context:
                SaleService().add_sale_item(
                    session=session,
                    current_user=user,
                    sale_id=self.sale_id,
                    product_id=self.product_id,
                    quantity=5,
                )

            self.assertEqual(
                str(context.exception),
                "Sale item quantity exceeds available inventory",
            )

    def test_inactive_product_is_rejected(self):
        with Session(self.engine) as session:
            user = session.get(User, self.user_id)

            product = session.get(Product, self.product_id)
            product.is_active = False
            session.flush()

            with self.assertRaises(ValueError) as context:
                SaleService().add_sale_item(
                    session=session,
                    current_user=user,
                    sale_id=self.sale_id,
                    product_id=self.product_id,
                    quantity=1,
                )

            self.assertEqual(
                str(context.exception),
                "Inactive products cannot be added to a sale",
            )

    def test_duplicate_product_in_sale_is_rejected(self):
        with Session(self.engine) as session:
            user = session.get(User, self.user_id)

            service = SaleService()

            service.add_sale_item(
                session=session,
                current_user=user,
                sale_id=self.sale_id,
                product_id=self.product_id,
                quantity=1,
            )

            with self.assertRaises(ValueError) as context:
                service.add_sale_item(
                    session=session,
                    current_user=user,
                    sale_id=self.sale_id,
                    product_id=self.product_id,
                    quantity=1,
                )

            self.assertEqual(
                str(context.exception),
                "Product is already present in this sale",
            )

            item_count = session.scalar(
                select(SaleItem).where(
                    SaleItem.sale_id == self.sale_id
                )
            )

            self.assertIsNotNone(item_count)


if __name__ == "__main__":
    unittest.main()