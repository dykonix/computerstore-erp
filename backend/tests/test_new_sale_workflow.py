import subprocess
import sys
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.routes.sales import _sale_response
from app.database.base import Base
from app.models.brand import Brand
from app.models.category import Category
from app.models.employee import Employee
from app.models.employee_store import EmployeeStore
from app.models.godown import Godown
from app.models.inventory import Inventory
from app.models.permission import Permission
from app.models.product import Product
from app.models.product_price import ProductPrice
from app.models.product_serial_number import ProductSerialNumber
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.sale_item_serial_number import SaleItemSerialNumber
from app.models.store import Store
from app.models.tenant import Tenant
from app.models.user import User
from app.models.user_role import UserRole
from app.services.authorization_service import PermissionDeniedError
from app.services.sale_service import SaleService

BACKEND_ROOT = Path(__file__).resolve().parents[1]


class ModelRegistryTests(unittest.TestCase):
    def test_package_import_registers_every_model_table(self):
        # Regression: sale_item_serial_numbers was missing from Base.metadata, so Alembic
        # reported no drift while GET /api/sales/{id} failed with HTTP 500.
        script = (
            "import importlib, pkgutil\n"
            "import app.models as models\n"
            "from app.database.base import Base\n"
            "registered = set(Base.metadata.tables)\n"
            "for module in pkgutil.iter_modules(models.__path__):\n"
            "    importlib.import_module(f'app.models.{module.name}')\n"
            "print(sorted(set(Base.metadata.tables) - registered))\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=BACKEND_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(result.stdout.strip(), "[]")


class NewSaleWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(cls.engine)
        cls.engine.dispose()

    def setUp(self):
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)

        with Session(self.engine) as session:
            tenant = Tenant(name="Tenant")
            other_tenant = Tenant(name="Other Tenant")
            ten_percent = Category(name="Laptop", gst_rate=Decimal("10.00"))
            zero_rated = Category(name="Books", gst_rate=Decimal("0.00"))
            unconfigured = Category(name="Gadgets", gst_rate=None)
            brand = Brand(name="HP")
            session.add_all(
                [tenant, other_tenant, ten_percent, zero_rated, unconfigured, brand]
            )
            session.flush()

            employee = Employee(
                tenant_id=tenant.id, email="s@example.com", name="Seller", is_active=True
            )
            main = Store(tenant_id=tenant.id, name="Main", is_active=True)
            second = Store(tenant_id=tenant.id, name="Second", is_active=True)
            unassigned = Store(tenant_id=tenant.id, name="Unassigned", is_active=True)
            foreign_store = Store(tenant_id=other_tenant.id, name="Foreign", is_active=True)
            godown = Godown(tenant_id=tenant.id, name="Back Godown", is_active=True)
            permission = Permission(code="sell", description="Sell")
            role = Role(tenant_id=tenant.id, name="Sales", is_active=True)
            session.add_all(
                [employee, main, second, unassigned, foreign_store, godown, permission, role]
            )
            session.flush()

            user = User(
                tenant_id=tenant.id,
                username="seller",
                email="seller@example.com",
                mobile="9999999999",
                password_hash="x",
                employee_id=employee.id,
                is_active=True,
            )
            session.add(user)
            session.flush()
            session.add_all(
                [
                    EmployeeStore(employee_id=employee.id, store_id=main.id),
                    EmployeeStore(employee_id=employee.id, store_id=second.id),
                    UserRole(user_id=user.id, role_id=role.id),
                    RolePermission(
                        role_id=role.id, permission_id=permission.id, scope="assigned_stores"
                    ),
                ]
            )

            def product(sku, name, category, **extra):
                return Product(
                    tenant_id=tenant.id,
                    category_id=category.id,
                    brand_id=brand.id,
                    sku=sku,
                    name=name,
                    **extra,
                )

            laptop = product("LAP-1", "Laptop", ten_percent)
            book = product("BK-1", "Book", zero_rated)
            gadget = product("GD-1", "Gadget", unconfigured)
            serialized = product("SER-1", "Serialized", ten_percent, requires_serial_number=True)
            session.add_all([laptop, book, gadget, serialized])
            session.flush()

            for item in (laptop, book, gadget, serialized):
                session.add(
                    ProductPrice(
                        product_id=item.id,
                        cost_price=Decimal("600.00"),
                        sale_price=Decimal("1000.00"),
                        minimum_sale_price=Decimal("900.00"),
                        valid_from=date.today(),
                    )
                )
                session.add(
                    Inventory(
                        tenant_id=tenant.id,
                        product_id=item.id,
                        store_id=main.id,
                        quantity=10,
                        reserved_quantity=0,
                    )
                )
            session.commit()

            self.tenant_id = tenant.id
            self.other_tenant_id = other_tenant.id
            self.user_id = user.id
            self.main_id = main.id
            self.second_id = second.id
            self.unassigned_id = unassigned.id
            self.foreign_store_id = foreign_store.id
            self.godown_id = godown.id
            self.laptop_id = laptop.id
            self.book_id = book.id
            self.gadget_id = gadget.id
            self.serialized_id = serialized.id

    def new_sale(self, session):
        user = session.get(User, self.user_id)
        sale = SaleService().create_sale(session, user, self.main_id)
        session.flush()
        return user, sale

    def add(self, session, user, sale, product_id, quantity=1, **kwargs):
        return SaleService().add_sale_item(
            session=session,
            current_user=user,
            sale_id=sale.id,
            product_id=product_id,
            quantity=quantity,
            **kwargs,
        )

    def test_configured_category_rate_reaches_inclusive_gst_calculation(self):
        with Session(self.engine) as session:
            user, sale = self.new_sale(session)
            item = self.add(session, user, sale, self.laptop_id)

            self.assertEqual(item.gst_rate, Decimal("10.00"))
            self.assertEqual(item.line_total, Decimal("1000.00"))
            self.assertEqual(item.gst_amount, Decimal("90.91"))
            self.assertEqual(sale.taxable_amount, Decimal("909.09"))
            self.assertEqual(sale.total_amount, Decimal("1000.00"))

    def test_line_and_sale_amounts_reconcile_across_categories(self):
        with Session(self.engine) as session:
            user, sale = self.new_sale(session)
            self.add(session, user, sale, self.laptop_id, quantity=3)
            self.add(session, user, sale, self.book_id, quantity=2)
            lines = SaleService().sale_repository.list_sale_items(session, sale.id)

            self.assertEqual(
                sale.total_amount, sum((line.line_total for line in lines), Decimal("0.00"))
            )
            self.assertEqual(
                sale.gst_amount, sum((line.gst_amount for line in lines), Decimal("0.00"))
            )
            self.assertEqual(sale.taxable_amount + sale.gst_amount, sale.total_amount)
            zero_rated_line = next(line for line in lines if line.product_id == self.book_id)
            self.assertEqual(zero_rated_line.gst_amount, Decimal("0.00"))

    def test_missing_rate_is_rejected_and_names_the_category(self):
        with Session(self.engine) as session:
            user, sale = self.new_sale(session)
            with self.assertRaisesRegex(ValueError, "category 'Gadgets'"):
                self.add(session, user, sale, self.gadget_id)

    def test_product_without_promotion_can_be_added_reserved_and_sold(self):
        with Session(self.engine) as session:
            user, sale = self.new_sale(session)
            item = self.add(session, user, sale, self.laptop_id, quantity=2)
            self.assertEqual((item.quantity, item.promotion_id), (2, None))
            self.assertFalse(item.is_promotion_benefit)

            service = SaleService()
            service.reserve_sale(session, user, sale.id)
            inventory = session.scalar(
                select(Inventory).where(
                    Inventory.product_id == self.laptop_id,
                    Inventory.store_id == self.main_id,
                )
            )
            self.assertEqual(inventory.reserved_quantity, 2)

            service.add_sale_payment(
                session=session,
                current_user=user,
                sale_id=sale.id,
                payment_mode="CASH",
                amount=sale.payable_amount,
            )
            service.confirm_sale(session=session, current_user=user, sale_id=sale.id)
            self.assertEqual((inventory.quantity, inventory.reserved_quantity), (8, 0))

    def test_saved_item_stays_visible_after_a_duplicate_attempt(self):
        with Session(self.engine) as session:
            user, sale = self.new_sale(session)
            self.add(session, user, sale, self.laptop_id)
            with self.assertRaisesRegex(ValueError, "already present"):
                self.add(session, user, sale, self.laptop_id)

            response = _sale_response(session, sale)
            self.assertEqual([item.product_id for item in response.items], [self.laptop_id])

    def test_promotion_benefit_line_does_not_block_buying_that_product(self):
        with Session(self.engine) as session:
            user, sale = self.new_sale(session)
            source = self.add(session, user, sale, self.laptop_id)
            session.add(
                SaleItem(
                    sale_id=sale.id,
                    product_id=self.book_id,
                    promotion_benefit_id=1,
                    promotion_benefit_name="Book",
                    promotion_source_sale_item_id=source.id,
                    promotion_benefit_source="MANUFACTURER",
                    is_promotion_benefit=True,
                    quantity=1,
                    configured_unit_price=Decimal("0.00"),
                    configured_minimum_price=Decimal("0.00"),
                    actual_unit_price=Decimal("0.00"),
                    is_free_product=True,
                    cost_price=Decimal("0.00"),
                    gst_rate=Decimal("0.00"),
                    gst_amount=Decimal("0.00"),
                    discount_amount=Decimal("0.00"),
                    line_total=Decimal("0.00"),
                )
            )
            session.flush()

            purchased = self.add(session, user, sale, self.book_id)
            self.assertFalse(purchased.is_promotion_benefit)

    def test_sale_response_serializes_items_and_serials(self):
        # Regression for the HTTP 500 raised by GET /api/sales/{id} when a sale has items.
        with Session(self.engine) as session:
            user, sale = self.new_sale(session)
            plain = self.add(session, user, sale, self.laptop_id)
            serialized = self.add(session, user, sale, self.serialized_id)
            serial = ProductSerialNumber(
                tenant_id=self.tenant_id,
                product_id=self.serialized_id,
                serial_number="SN-1",
                status="SOLD",
            )
            session.add(serial)
            session.flush()
            session.add(
                SaleItemSerialNumber(
                    sale_item_id=serialized.id, product_serial_number_id=serial.id
                )
            )
            session.flush()

            response = _sale_response(session, sale)
            by_id = {item.id: item for item in response.items}
            self.assertEqual(by_id[plain.id].serial_numbers, [])
            self.assertFalse(by_id[plain.id].requires_serial_number)
            self.assertEqual(by_id[serialized.id].serial_numbers, ["SN-1"])
            self.assertTrue(by_id[serialized.id].requires_serial_number)

    def add_stock(self, session, **kwargs):
        session.add(
            Inventory(
                tenant_id=kwargs.pop("tenant_id", self.tenant_id),
                product_id=self.laptop_id,
                **kwargs,
            )
        )

    def test_other_locations_remain_visible_when_current_store_has_zero_stock(self):
        with Session(self.engine) as session:
            main_row = session.scalar(
                select(Inventory).where(
                    Inventory.product_id == self.laptop_id,
                    Inventory.store_id == self.main_id,
                )
            )
            main_row.quantity = 0
            self.add_stock(session, store_id=self.second_id, quantity=5, reserved_quantity=2)
            self.add_stock(session, godown_id=self.godown_id, quantity=4, reserved_quantity=0)
            self.add_stock(session, store_id=self.unassigned_id, quantity=9, reserved_quantity=0)
            session.commit()

        with Session(self.engine) as session:
            user = session.get(User, self.user_id)
            result = SaleService().get_product_availability(
                session, user, self.main_id, self.laptop_id
            )

            self.assertEqual(result["current_store"]["available_quantity"], 0)
            others = {
                entry["location_name"]: entry for entry in result["other_locations"]
            }
            # Reserved units are excluded, the godown is listed, and an unauthorized store is hidden.
            self.assertEqual(set(others), {"Second", "Back Godown"})
            self.assertEqual(others["Second"]["available_quantity"], 3)
            self.assertEqual(others["Second"]["reserved_quantity"], 2)
            self.assertEqual(others["Back Godown"]["available_quantity"], 4)

    def test_current_store_availability_excludes_reserved_and_hides_exhausted_others(self):
        with Session(self.engine) as session:
            main_row = session.scalar(
                select(Inventory).where(
                    Inventory.product_id == self.laptop_id,
                    Inventory.store_id == self.main_id,
                )
            )
            main_row.quantity = 6
            main_row.reserved_quantity = 4
            self.add_stock(session, store_id=self.second_id, quantity=2, reserved_quantity=2)
            session.commit()

        with Session(self.engine) as session:
            user = session.get(User, self.user_id)
            result = SaleService().get_product_availability(
                session, user, self.main_id, self.laptop_id
            )
            self.assertEqual(result["current_store"]["quantity"], 6)
            self.assertEqual(result["current_store"]["available_quantity"], 2)
            self.assertEqual(result["other_locations"], [])

    def test_availability_without_a_current_store_row_reports_zero(self):
        with Session(self.engine) as session:
            user = session.get(User, self.user_id)
            result = SaleService().get_product_availability(
                session, user, self.second_id, self.laptop_id
            )
            self.assertEqual(result["current_store"]["location_name"], "Second")
            self.assertEqual(result["current_store"]["available_quantity"], 0)

    def test_availability_enforces_store_permission_and_tenant_isolation(self):
        with Session(self.engine) as session:
            self.add_stock(
                session,
                tenant_id=self.other_tenant_id,
                store_id=self.foreign_store_id,
                quantity=50,
                reserved_quantity=0,
            )
            session.commit()

        with Session(self.engine) as session:
            user = session.get(User, self.user_id)
            service = SaleService()
            with self.assertRaises(PermissionDeniedError):
                service.get_product_availability(
                    session, user, self.unassigned_id, self.laptop_id
                )
            result = service.get_product_availability(
                session, user, self.main_id, self.laptop_id
            )
            self.assertEqual(result["other_locations"], [])


if __name__ == "__main__":
    unittest.main()
