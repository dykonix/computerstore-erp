import unittest

from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

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
from app.models.product_price import ProductPrice
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.sale_payment import SalePayment
from app.models.store import Store
from app.models.tenant import Tenant
from app.models.user import User
from app.models.user_role import UserRole
from app.services.sale_service import SaleService


class SaleConfirmationServiceTests(unittest.TestCase):
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
                gst_rate=Decimal("18.00"),
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
                sku="HP-001",
                name="HP Laptop",
                is_active=True,
            )

            customer = Customer(
                tenant_id=tenant.id,
                name="Test Customer",
                mobile="9999999999",
                is_active=True,
            )

            role = Role(
                tenant_id=tenant.id,
                name="Sales",
                description="Sales role",
                is_active=True,
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
            ])

            session.flush()

            product_price = ProductPrice(
                product_id=product.id,
                cost_price=Decimal("800.00"),
                sale_price=Decimal("1000.00"),
                minimum_sale_price=Decimal("900.00"),
                valid_from=date.today(),
                valid_to=None,
            )

            inventory = Inventory(
                tenant_id=tenant.id,
                product_id=product.id,
                store_id=store.id,
                quantity=5,
                reserved_quantity=1,
            )

            session.add_all([
                product_price,
                inventory,
            ])

            session.flush()

            sale = Sale(
                tenant_id=tenant.id,
                store_id=store.id,
                customer_id=customer.id,
                employee_id=employee.id,
                status="DRAFT",
                subtotal=Decimal("2000.00"),
                invoice_discount=Decimal("0.00"),
                taxable_amount=Decimal("1640.00"),
                gst_amount=Decimal("360.00"),
                total_amount=Decimal("2000.00"),
                payable_amount=Decimal("2000.00"),
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
            self.user_id = user.id
            self.sale_id = sale.id

    def reserve_sale(self, session):
        user = session.get(User, self.user_id)

        return SaleService().reserve_sale(
            session,
            user,
            self.sale_id,
        )

    def add_full_payment(self, session):
        user = session.get(User, self.user_id)

        return SaleService().add_sale_payment(
            session=session,
            current_user=user,
            sale_id=self.sale_id,
            payment_mode="UPI",
            amount=Decimal("2000.00"),
            transaction_reference="UPI-001",
        )

    def test_confirmation_is_rejected_for_draft_sale(self):
        with Session(self.engine) as session:
            user = session.get(User, self.user_id)

            with self.assertRaises(ValueError) as context:
                SaleService().confirm_sale(
                    session=session,
                    current_user=user,
                    sale_id=self.sale_id,
                )

            self.assertEqual(
                str(context.exception),
                "Only reserved sales can be confirmed",
            )

    def test_confirmation_is_rejected_when_payment_is_incomplete(self):
        with Session(self.engine) as session:
            self.reserve_sale(session)

            user = session.get(User, self.user_id)

            SaleService().add_sale_payment(
                session=session,
                current_user=user,
                sale_id=self.sale_id,
                payment_mode="UPI",
                amount=Decimal("1000.00"),
                transaction_reference="UPI-001",
            )

            with self.assertRaises(ValueError) as context:
                SaleService().confirm_sale(
                    session=session,
                    current_user=user,
                    sale_id=self.sale_id,
                )

            self.assertEqual(
                str(context.exception),
                "Sale cannot be confirmed until full payment is received",
            )

            session.rollback()

    def test_fully_paid_sale_is_confirmed_and_inventory_is_reduced(self):
        with Session(self.engine) as session:
            self.reserve_sale(session)
            self.add_full_payment(session)

            user = session.get(User, self.user_id)

            sale = SaleService().confirm_sale(
                session=session,
                current_user=user,
                sale_id=self.sale_id,
            )

            session.commit()

            self.assertEqual(
                sale.status,
                "CONFIRMED",
            )

        with Session(self.engine) as session:
            sale = session.get(
                Sale,
                self.sale_id,
            )

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
                    InventoryMovement.movement_type == "SALE",
                    InventoryMovement.reference_type == "SALE",
                    InventoryMovement.reference_id == self.sale_id,
                )
            )

            self.assertEqual(
                sale.status,
                "CONFIRMED",
            )

            self.assertIsNotNone(inventory)

            self.assertEqual(
                inventory.quantity,
                3,
            )

            self.assertEqual(
                inventory.reserved_quantity,
                1,
            )

            self.assertIsNotNone(movement)

            self.assertEqual(
                movement.quantity,
                2,
            )

            self.assertEqual(
                movement.from_store_id,
                self.store_id,
            )

            self.assertEqual(
                movement.performed_by_employee_id,
                self.employee_id,
            )

    def test_confirmation_is_rejected_after_already_confirmed(self):
        with Session(self.engine) as session:
            self.reserve_sale(session)
            self.add_full_payment(session)

            user = session.get(User, self.user_id)

            SaleService().confirm_sale(
                session=session,
                current_user=user,
                sale_id=self.sale_id,
            )

            session.commit()

        with Session(self.engine) as session:
            user = session.get(User, self.user_id)

            with self.assertRaises(ValueError) as context:
                SaleService().confirm_sale(
                    session=session,
                    current_user=user,
                    sale_id=self.sale_id,
                )

            self.assertEqual(
                str(context.exception),
                "Only reserved sales can be confirmed",
            )

    def test_confirmed_sale_can_be_delivered(self):
        with Session(self.engine) as session:
            self.reserve_sale(session)
            self.add_full_payment(session)
            user = session.get(User, self.user_id)
            SaleService().confirm_sale(
                session=session,
                current_user=user,
                sale_id=self.sale_id,
            )
            session.commit()

        with Session(self.engine) as session:
            user = session.get(User, self.user_id)
            sale = SaleService().deliver_sale(
                session=session,
                current_user=user,
                sale_id=self.sale_id,
            )
            session.commit()

            self.assertEqual(sale.status, "DELIVERED")

    def test_upi_cashback_requires_upi_payment(self):
        with Session(self.engine) as session:
            sale = session.get(Sale, self.sale_id)
            sale.cashback_amount = Decimal("100.00")
            sale.payable_amount = Decimal("1900.00")
            session.commit()
            self.reserve_sale(session)
            user = session.get(User, self.user_id)
            SaleService().add_sale_payment(
                session=session,
                current_user=user,
                sale_id=self.sale_id,
                payment_mode="CASH",
                amount=Decimal("1900.00"),
            )

            with self.assertRaises(ValueError) as context:
                SaleService().confirm_sale(
                    session=session,
                    current_user=user,
                    sale_id=self.sale_id,
                )

            self.assertEqual(
                str(context.exception),
                "UPI cashback requires a UPI payment",
            )

    def test_multiple_payments_can_complete_confirmation(self):
        with Session(self.engine) as session:
            self.reserve_sale(session)

            user = session.get(User, self.user_id)

            service = SaleService()

            first_payment = service.add_sale_payment(
                session=session,
                current_user=user,
                sale_id=self.sale_id,
                payment_mode="UPI",
                amount=Decimal("1000.00"),
                transaction_reference="UPI-001",
            )

            second_payment = service.add_sale_payment(
                session=session,
                current_user=user,
                sale_id=self.sale_id,
                payment_mode="CASH",
                amount=Decimal("1000.00"),
            )

            self.assertEqual(
                first_payment.amount,
                Decimal("1000.00"),
            )

            self.assertEqual(
                second_payment.amount,
                Decimal("1000.00"),
            )

            sale = service.confirm_sale(
                session=session,
                current_user=user,
                sale_id=self.sale_id,
            )

            session.commit()

            self.assertEqual(
                sale.status,
                "CONFIRMED",
            )

            payments = session.scalars(
                select(SalePayment)
                .where(
                    SalePayment.sale_id == self.sale_id,
                )
                .order_by(SalePayment.id)
            ).all()

            self.assertEqual(
                len(payments),
                2,
            )

            self.assertEqual(
                sum(
                    (payment.amount for payment in payments),
                    Decimal("0.00"),
                ),
                Decimal("2000.00"),
            )


if __name__ == "__main__":
    unittest.main()