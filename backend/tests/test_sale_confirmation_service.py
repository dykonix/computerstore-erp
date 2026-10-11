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
from app.models.product_serial_number import ProductSerialNumber
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
            session.flush()

            session.commit()

            self.tenant_id = tenant.id
            self.employee_id = employee.id
            self.store_id = store.id
            self.product_id = product.id
            self.user_id = user.id
            self.sale_id = sale.id
            self.sale_item_id = sale_item.id

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

    def test_manufacturer_shipped_benefit_does_not_reserve_or_consume_store_stock(self):
        with Session(self.engine) as session:
            source_item = session.get(SaleItem, self.sale_item_id)
            source_product = session.get(Product, self.product_id)
            gift_product = Product(
                tenant_id=self.tenant_id,
                category_id=source_product.category_id,
                brand_id=source_product.brand_id,
                sku="MFG-GIFT-001",
                name="Manufacturer Gift",
            )
            session.add(gift_product)
            session.flush()
            session.add(
                SaleItem(
                    sale_id=self.sale_id,
                    product_id=gift_product.id,
                    promotion_benefit_id=1,
                    promotion_benefit_name=gift_product.name,
                    promotion_source_sale_item_id=source_item.id,
                    is_promotion_benefit=True,
                    promotion_benefit_source="MANUFACTURER",
                    quantity=source_item.quantity,
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
            gift_product_id = gift_product.id
            session.commit()

        with Session(self.engine) as session:
            self.reserve_sale(session)
            inventory = session.scalar(
                select(Inventory).where(
                    Inventory.product_id == self.product_id,
                    Inventory.store_id == self.store_id,
                )
            )
            self.assertEqual(inventory.reserved_quantity, 3)
            self.assertIsNone(
                session.scalar(
                    select(Inventory).where(
                        Inventory.product_id == gift_product_id,
                        Inventory.store_id == self.store_id,
                    )
                )
            )
            self.add_full_payment(session)
            user = session.get(User, self.user_id)
            SaleService().confirm_sale(
                session=session,
                current_user=user,
                sale_id=self.sale_id,
            )
            session.commit()

        with Session(self.engine) as session:
            gift_movements = session.scalars(
                select(InventoryMovement).where(
                    InventoryMovement.product_id == gift_product_id,
                    InventoryMovement.reference_id == self.sale_id,
                )
            ).all()
            self.assertEqual(gift_movements, [])

    def test_store_supplied_benefit_reserves_and_consumes_inventory(self):
        with Session(self.engine) as session:
            source_item = session.get(SaleItem, self.sale_item_id)
            source_product = session.get(Product, self.product_id)
            gift_product = Product(
                tenant_id=self.tenant_id,
                category_id=source_product.category_id,
                brand_id=source_product.brand_id,
                sku="STORE-GIFT-001",
                name="Store Gift",
            )
            session.add(gift_product)
            session.flush()
            session.add_all(
                [
                    Inventory(
                        tenant_id=self.tenant_id,
                        product_id=gift_product.id,
                        store_id=self.store_id,
                        quantity=2,
                        reserved_quantity=0,
                    ),
                    SaleItem(
                        sale_id=self.sale_id,
                        product_id=gift_product.id,
                        promotion_benefit_id=2,
                        promotion_benefit_name=gift_product.name,
                        promotion_source_sale_item_id=source_item.id,
                        promotion_benefit_source="STORE",
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
                    ),
                ]
            )
            gift_product_id = gift_product.id
            session.commit()

        with Session(self.engine) as session:
            self.reserve_sale(session)
            inventory = session.scalar(
                select(Inventory).where(
                    Inventory.product_id == gift_product_id,
                    Inventory.store_id == self.store_id,
                )
            )
            self.assertEqual((inventory.quantity, inventory.reserved_quantity), (2, 1))
            self.add_full_payment(session)
            user = session.get(User, self.user_id)
            SaleService().confirm_sale(
                session=session,
                current_user=user,
                sale_id=self.sale_id,
            )
            session.commit()

        with Session(self.engine) as session:
            inventory = session.scalar(
                select(Inventory).where(
                    Inventory.product_id == gift_product_id,
                    Inventory.store_id == self.store_id,
                )
            )
            movement = session.scalar(
                select(InventoryMovement).where(
                    InventoryMovement.product_id == gift_product_id,
                    InventoryMovement.movement_type == "SALE",
                    InventoryMovement.reference_id == self.sale_id,
                )
            )
            self.assertEqual((inventory.quantity, inventory.reserved_quantity), (1, 0))
            self.assertEqual(movement.quantity, 1)

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

    def test_delivery_saves_one_serial_per_serialized_unit(self):
        with Session(self.engine) as session:
            product = session.get(Product, self.product_id)
            product.requires_serial_number = True
            session.get(Sale, self.sale_id).status = "CONFIRMED"
            session.commit()

        with Session(self.engine) as session:
            user = session.get(User, self.user_id)
            sale = SaleService().deliver_sale(
                session=session,
                current_user=user,
                sale_id=self.sale_id,
                serial_numbers_by_item={
                    self.sale_item_id: ["HP-SN-UNIT-1", "HP-SN-UNIT-2"]
                },
                allow_missing_serial_numbers=False,
            )
            serials = SaleService().sale_repository.list_sale_item_serials(
                session, self.sale_item_id
            )
            self.assertEqual(sale.status, "DELIVERED")
            self.assertEqual(
                [serial.serial_number for serial in serials],
                ["HP-SN-UNIT-1", "HP-SN-UNIT-2"],
            )
            self.assertTrue(all(serial.status == "SOLD" for serial in serials))

    def test_delivery_rejects_serial_assigned_to_another_sale(self):
        with Session(self.engine) as session:
            product = session.get(Product, self.product_id)
            product.requires_serial_number = True
            session.get(Sale, self.sale_id).status = "CONFIRMED"
            serial = ProductSerialNumber(
                tenant_id=self.tenant_id,
                product_id=self.product_id,
                serial_number="HP-SN-TAKEN",
                status="SOLD",
            )
            session.add(serial)
            session.commit()

        with Session(self.engine) as session:
            user = session.get(User, self.user_id)
            with self.assertRaisesRegex(ValueError, "not available"):
                SaleService().deliver_sale(
                    session=session,
                    current_user=user,
                    sale_id=self.sale_id,
                    serial_numbers_by_item={self.sale_item_id: ["HP-SN-TAKEN"]},
                    allow_missing_serial_numbers=True,
                )

    def test_delivery_rejects_serial_for_another_product(self):
        with Session(self.engine) as session:
            product = session.get(Product, self.product_id)
            product.requires_serial_number = True
            other_product = Product(
                tenant_id=self.tenant_id,
                category_id=product.category_id,
                brand_id=product.brand_id,
                sku="OTHER-SERIAL-PRODUCT",
                name="Other Product",
            )
            session.add(other_product)
            session.flush()
            session.add(
                ProductSerialNumber(
                    tenant_id=self.tenant_id,
                    product_id=other_product.id,
                    serial_number="OTHER-PRODUCT-SERIAL",
                    status="IN_STOCK",
                )
            )
            session.get(Sale, self.sale_id).status = "CONFIRMED"
            session.commit()

        with Session(self.engine) as session:
            user = session.get(User, self.user_id)
            with self.assertRaisesRegex(ValueError, "belongs to another product"):
                SaleService().deliver_sale(
                    session=session,
                    current_user=user,
                    sale_id=self.sale_id,
                    serial_numbers_by_item={
                        self.sale_item_id: ["OTHER-PRODUCT-SERIAL"]
                    },
                    allow_missing_serial_numbers=True,
                )

    def test_missing_serials_warn_but_delivery_can_proceed_when_allowed(self):
        with Session(self.engine) as session:
            product = session.get(Product, self.product_id)
            product.requires_serial_number = True
            session.get(Sale, self.sale_id).status = "CONFIRMED"
            session.commit()

        with Session(self.engine) as session:
            user = session.get(User, self.user_id)
            with self.assertRaisesRegex(ValueError, "Serial numbers are missing"):
                SaleService().deliver_sale(
                    session=session,
                    current_user=user,
                    sale_id=self.sale_id,
                    serial_numbers_by_item={},
                    allow_missing_serial_numbers=False,
                )

        with Session(self.engine) as session:
            user = session.get(User, self.user_id)
            sale = SaleService().deliver_sale(
                session=session,
                current_user=user,
                sale_id=self.sale_id,
                serial_numbers_by_item={},
                allow_missing_serial_numbers=True,
            )
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