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