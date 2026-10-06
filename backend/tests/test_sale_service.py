import unittest
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine

from app.database.base import Base
from app.models.brand import Brand
from app.models.category import Category
from app.models.customer import Customer
from app.models.employee import Employee
from app.models.employee_store import EmployeeStore
from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement
from app.models.permission import Permission
from app.models.product import Product
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.store import Store
from app.models.tenant import Tenant
from app.models.user import User
from app.models.user_role import UserRole
from app.services.sale_service import SaleService


class SaleServiceTests(unittest.TestCase):
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
            tenant = Tenant(
                name="Tenant A",
            )

            category = Category(
                name="Laptops",
            )

            brand = Brand(
                name="HP",
            )

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
            )

            store = Store(
                tenant_id=tenant.id,
                name="Main Store",
            )

            product = Product(
                tenant_id=tenant.id,
                category_id=category.id,
                brand_id=brand.id,
                sku="HP-001",
                name="HP Laptop",
            )

            customer = Customer(
                tenant_id=tenant.id,
                name="Test Customer",
                mobile="9999999999",
            )

            inactive_customer = Customer(
                tenant_id=tenant.id,
                name="Inactive Customer",
                mobile="9999999998",
                is_active=False,
            )

            role = Role(
                tenant_id=tenant.id,
                name="Sales",
                description="Sales role",
            )

            permission = Permission(
                code="sell",
                description="Create and process sales",
            )

            session.add_all([
                employee,
                store,
                product,
                customer,
                inactive_customer,
                role,
                permission,
            ])

            session.flush()

            user = User(
                tenant_id=tenant.id,
                username="sales-user",
                password_hash="test-only-hash",
                email="sales-user@example.com",
                mobile="9999999997",
                employee_id=employee.id,
                is_active=True,
            )

            session.add(user)
            session.flush()

            session.add_all([
                UserRole(
                    user_id=user.id,
                    role_id=role.id,
                ),
                RolePermission(
                    role_id=role.id,
                    permission_id=permission.id,
                    scope="assigned_stores",
                ),
                EmployeeStore(
                    employee_id=employee.id,
                    store_id=store.id,
                ),
                Inventory(
                    tenant_id=tenant.id,
                    product_id=product.id,
                    store_id=store.id,
                    quantity=5,
                    reserved_quantity=1,
                ),
            ])

            sale = Sale(
                tenant_id=tenant.id,
                store_id=store.id,
                customer_id=customer.id,
                employee_id=employee.id,
                status="DRAFT",
                subtotal=Decimal("2000.00"),
                invoice_discount=Decimal("0.00"),
                taxable_amount=Decimal("2000.00"),
                gst_amount=Decimal("360.00"),
                total_amount=Decimal("2360.00"),
            )

            session.add(sale)
            session.flush()

            sale_item = SaleItem(
                sale_id=sale.id,
                product_id=product.id,
                quantity=2,
                configured_unit_price=Decimal("1000.00"),
                actual_unit_price=Decimal("1000.00"),
                cost_price=Decimal("800.00"),
                gst_rate=Decimal("18.00"),
                gst_amount=Decimal("360.00"),
                discount_amount=Decimal("0.00"),
                line_total=Decimal("2000.00"),
            )

            session.add(sale_item)
            session.commit()

            self.tenant_id = tenant.id
            self.employee_id = employee.id
            self.store_id = store.id
            self.product_id = product.id
            self.customer_id = customer.id
            self.inactive_customer_id = inactive_customer.id
            self.user_id = user.id
            self.sale_id = sale.id

    def test_create_draft_sale(self):
        service = SaleService()

        with Session(self.engine) as session:
            user = session.get(User, self.user_id)

            sale = service.create_sale(
                session=session,
                current_user=user,
                store_id=self.store_id,
                customer_id=self.customer_id,
            )

            session.commit()

            self.assertIsNotNone(sale.id)
            self.assertEqual(sale.tenant_id, self.tenant_id)
            self.assertEqual(sale.store_id, self.store_id)
            self.assertEqual(sale.customer_id, self.customer_id)
            self.assertEqual(sale.employee_id, self.employee_id)
            self.assertEqual(sale.status, "DRAFT")

            self.assertEqual(sale.subtotal, Decimal("0.00"))
            self.assertEqual(sale.invoice_discount, Decimal("0.00"))
            self.assertEqual(sale.taxable_amount, Decimal("0.00"))
            self.assertEqual(sale.gst_amount, Decimal("0.00"))
            self.assertEqual(sale.total_amount, Decimal("0.00"))

    def test_create_draft_sale_without_customer(self):
        service = SaleService()

        with Session(self.engine) as session:
            user = session.get(User, self.user_id)

            sale = service.create_sale(
                session=session,
                current_user=user,
                store_id=self.store_id,
            )

            session.commit()

            self.assertIsNotNone(sale.id)
            self.assertEqual(sale.tenant_id, self.tenant_id)
            self.assertEqual(sale.store_id, self.store_id)
            self.assertIsNone(sale.customer_id)
            self.assertEqual(sale.employee_id, self.employee_id)
            self.assertEqual(sale.status, "DRAFT")

            self.assertEqual(sale.subtotal, Decimal("0.00"))
            self.assertEqual(sale.invoice_discount, Decimal("0.00"))
            self.assertEqual(sale.taxable_amount, Decimal("0.00"))
            self.assertEqual(sale.gst_amount, Decimal("0.00"))
            self.assertEqual(sale.total_amount, Decimal("0.00"))

    def test_create_sale_rejected_for_inactive_customer(self):
        service = SaleService()

        with Session(self.engine) as session:
            user = session.get(User, self.user_id)

            with self.assertRaises(ValueError) as context:
                service.create_sale(
                    session=session,
                    current_user=user,
                    store_id=self.store_id,
                    customer_id=self.inactive_customer_id,
                )

            self.assertEqual(
                str(context.exception),
                "Inactive customers cannot be used for new sales",
            )

            session.rollback()

        with Session(self.engine) as session:
            sales_count = session.scalar(
                select(func.count()).select_from(Sale)
            )

            self.assertEqual(sales_count, 1)

    def test_successful_sale_reservation(self):
        service = SaleService()

        with Session(self.engine) as session:
            user = session.get(User, self.user_id)

            sale = service.reserve_sale(
                session,
                user,
                self.sale_id,
            )

            session.commit()

            self.assertEqual(sale.status, "RESERVED")
            self.assertIsNotNone(sale.reserved_at)
            self.assertIsNotNone(sale.reservation_warning_at)
            self.assertIsNotNone(sale.reservation_expires_at)

        with Session(self.engine) as session:
            inventory = session.scalar(
                select(Inventory).where(
                    Inventory.tenant_id == self.tenant_id,
                    Inventory.product_id == self.product_id,
                    Inventory.store_id == self.store_id,
                )
            )

            self.assertIsNotNone(inventory)
            self.assertEqual(inventory.quantity, 5)
            self.assertEqual(inventory.reserved_quantity, 3)

            movement = session.scalar(
                select(InventoryMovement).where(
                    InventoryMovement.tenant_id == self.tenant_id,
                    InventoryMovement.product_id == self.product_id,
                    InventoryMovement.movement_type == "RESERVATION",
                    InventoryMovement.reference_type == "SALE",
                    InventoryMovement.reference_id == self.sale_id,
                )
            )

            self.assertIsNotNone(movement)
            self.assertEqual(movement.quantity, 2)
            self.assertEqual(movement.from_store_id, self.store_id)
            self.assertEqual(
                movement.performed_by_employee_id,
                self.employee_id,
            )

    def test_reservation_rejected_when_inventory_is_insufficient(self):
        service = SaleService()

        with Session(self.engine) as session:
            sale_item = session.scalar(
                select(SaleItem).where(
                    SaleItem.sale_id == self.sale_id
                )
            )

            sale_item.quantity = 5
            session.commit()

        with Session(self.engine) as session:
            user = session.get(User, self.user_id)

            with self.assertRaises(ValueError) as context:
                service.reserve_sale(
                    session,
                    user,
                    self.sale_id,
                )

            self.assertEqual(
                str(context.exception),
                "Insufficient available inventory",
            )

            session.rollback()

        with Session(self.engine) as session:
            sale = session.get(Sale, self.sale_id)

            inventory = session.scalar(
                select(Inventory).where(
                    Inventory.tenant_id == self.tenant_id,
                    Inventory.product_id == self.product_id,
                    Inventory.store_id == self.store_id,
                )
            )

            movement = session.scalar(
                select(InventoryMovement).where(
                    InventoryMovement.tenant_id == self.tenant_id,
                    InventoryMovement.product_id == self.product_id,
                    InventoryMovement.movement_type == "RESERVATION",
                    InventoryMovement.reference_type == "SALE",
                    InventoryMovement.reference_id == self.sale_id,
                )
            )

            self.assertEqual(sale.status, "DRAFT")
            self.assertEqual(inventory.quantity, 5)
            self.assertEqual(inventory.reserved_quantity, 1)
            self.assertIsNone(movement)

    def test_reservation_rejected_for_inactive_customer(self):
        service = SaleService()

        with Session(self.engine) as session:
            customer = session.get(
                Customer,
                self.customer_id,
            )

            customer.is_active = False
            session.commit()

        with Session(self.engine) as session:
            user = session.get(User, self.user_id)

            with self.assertRaises(ValueError) as context:
                service.reserve_sale(
                    session,
                    user,
                    self.sale_id,
                )

            self.assertEqual(
                str(context.exception),
                "Inactive customers cannot be used for new sales",
            )

            session.rollback()

        with Session(self.engine) as session:
            sale = session.get(Sale, self.sale_id)

            inventory = session.scalar(
                select(Inventory).where(
                    Inventory.tenant_id == self.tenant_id,
                    Inventory.product_id == self.product_id,
                    Inventory.store_id == self.store_id,
                )
            )

            movement = session.scalar(
                select(InventoryMovement).where(
                    InventoryMovement.tenant_id == self.tenant_id,
                    InventoryMovement.product_id == self.product_id,
                    InventoryMovement.movement_type == "RESERVATION",
                    InventoryMovement.reference_type == "SALE",
                    InventoryMovement.reference_id == self.sale_id,
                )
            )

            self.assertEqual(sale.status, "DRAFT")
            self.assertEqual(inventory.quantity, 5)
            self.assertEqual(inventory.reserved_quantity, 1)
            self.assertIsNone(movement)


if __name__ == "__main__":
    unittest.main()