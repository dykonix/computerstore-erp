import unittest
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
from app.models.permission import Permission
from app.models.product import Product
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


class SalePaymentServiceTests(unittest.TestCase):

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
            tenant = Tenant(name="Tenant A")

            category = Category(
                name="Laptops",
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
            self.customer_id = customer.id
            self.user_id = user.id
            self.sale_id = sale.id

    def reserve_sale(self, session):
        user = session.get(User, self.user_id)

        return SaleService().reserve_sale(
            session,
            user,
            self.sale_id,
        )

    def test_payment_is_rejected_for_draft_sale(self):
        with Session(self.engine) as session:
            user = session.get(User, self.user_id)

            with self.assertRaises(ValueError) as context:
                SaleService().add_sale_payment(
                    session=session,
                    current_user=user,
                    sale_id=self.sale_id,
                    payment_mode="UPI",
                    amount=Decimal("1000.00"),
                    transaction_reference="UPI-001",
                )

            self.assertEqual(
                str(context.exception),
                "Payments can only be recorded for reserved sales",
            )

    def test_payment_is_recorded_for_reserved_sale(self):
        with Session(self.engine) as session:
            self.reserve_sale(session)

            user = session.get(User, self.user_id)

            payment = SaleService().add_sale_payment(
                session=session,
                current_user=user,
                sale_id=self.sale_id,
                payment_mode="UPI",
                amount=Decimal("1000.00"),
                transaction_reference="UPI-001",
            )

            session.commit()

            self.assertIsNotNone(payment.id)
            self.assertEqual(payment.sale_id, self.sale_id)
            self.assertEqual(payment.payment_mode, "UPI")
            self.assertEqual(payment.amount, Decimal("1000.00"))
            self.assertEqual(
                payment.transaction_reference,
                "UPI-001",
            )

    def test_multiple_payments_are_allowed_up_to_sale_total(self):
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

            session.commit()

            self.assertEqual(
                first_payment.amount,
                Decimal("1000.00"),
            )

            self.assertEqual(
                second_payment.amount,
                Decimal("1000.00"),
            )

            payments = session.scalars(
                select(SalePayment)
                .where(SalePayment.sale_id == self.sale_id)
                .order_by(SalePayment.id)
            ).all()

            self.assertEqual(len(payments), 2)

            self.assertEqual(
                sum(
                    (payment.amount for payment in payments),
                    Decimal("0.00"),
                ),
                Decimal("2000.00"),
            )

    def test_overpayment_is_rejected(self):
        with Session(self.engine) as session:
            self.reserve_sale(session)

            user = session.get(User, self.user_id)
            service = SaleService()

            service.add_sale_payment(
                session=session,
                current_user=user,
                sale_id=self.sale_id,
                payment_mode="UPI",
                amount=Decimal("2000.00"),
                transaction_reference="UPI-002",
            )

            with self.assertRaises(ValueError) as context:
                service.add_sale_payment(
                    session=session,
                    current_user=user,
                    sale_id=self.sale_id,
                    payment_mode="CASH",
                    amount=Decimal("361.00"),
                )

            self.assertEqual(
                str(context.exception),
                "Payment amount cannot exceed remaining sale amount",
            )

            session.rollback()

        with Session(self.engine) as session:
            payments = session.scalars(
                select(SalePayment)
                .where(SalePayment.sale_id == self.sale_id)
            ).all()

            self.assertEqual(len(payments), 0)

    def test_zero_or_negative_payment_is_rejected(self):
        with Session(self.engine) as session:
            self.reserve_sale(session)

            user = session.get(User, self.user_id)

            for amount in (
                Decimal("0.00"),
                Decimal("-1.00"),
            ):
                with self.assertRaises(ValueError) as context:
                    SaleService().add_sale_payment(
                        session=session,
                        current_user=user,
                        sale_id=self.sale_id,
                        payment_mode="CASH",
                        amount=amount,
                    )

                self.assertEqual(
                    str(context.exception),
                    "Payment amount must be greater than zero",
                )

    def test_non_cash_payment_requires_transaction_reference(self):
        with Session(self.engine) as session:
            self.reserve_sale(session)
            user = session.get(User, self.user_id)

            with self.assertRaises(ValueError) as context:
                SaleService().add_sale_payment(
                    session=session,
                    current_user=user,
                    sale_id=self.sale_id,
                    payment_mode="UPI",
                    amount=Decimal("1000.00"),
                )

            self.assertEqual(
                str(context.exception),
                "Transaction reference is required for this payment mode",
            )

    def test_payment_mode_is_required(self):
        with Session(self.engine) as session:
            self.reserve_sale(session)

            user = session.get(User, self.user_id)

            with self.assertRaises(ValueError) as context:
                SaleService().add_sale_payment(
                    session=session,
                    current_user=user,
                    sale_id=self.sale_id,
                    payment_mode="   ",
                    amount=Decimal("1000.00"),
                )

            self.assertEqual(
                str(context.exception),
                "Payment mode is required",
            )


if __name__ == "__main__":
    unittest.main()