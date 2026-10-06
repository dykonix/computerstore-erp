import unittest

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.database.base import Base
from app.models.brand import Brand
from app.models.category import Category
from app.models.godown import Godown
from app.models.employee import Employee
from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement
from app.models.product import Product
from app.models.store import Store
from app.models.supplier import Supplier
from app.models.tenant import Tenant
from app.schemas.inventory import InventoryTransferCreate, OpeningStockCreate
from app.services.inventory_service import InventoryService, InventoryValidationError


class FailingMovementRepository:
    def __init__(self, service):
        self.delegate = service.repository

    def __getattr__(self, name):
        return getattr(self.delegate, name)

    def add_movement(self, session, movement):
        raise RuntimeError("movement failure")


class InventoryServiceTests(unittest.TestCase):
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
            other_tenant = Tenant(name="Other")
            category = Category(name="Laptop")
            brand = Brand(name="HP")
            product = Product(tenant_id=1, category_id=1, brand_id=1, sku="HP-1", name="HP Laptop")
            store = Store(tenant_id=1, name="Main Store")
            godown = Godown(tenant_id=1, name="Main Godown")
            other_store = Store(tenant_id=2, name="Other Store")
            supplier = Supplier(tenant_id=1, name="Active Supplier")
            inactive_supplier = Supplier(
                tenant_id=1, name="Inactive Supplier", is_active=False
            )
            other_supplier = Supplier(tenant_id=2, name="Other Tenant Supplier")
            session.add_all([tenant, other_tenant, category, brand])
            session.flush()
            product.tenant_id, product.category_id, product.brand_id = tenant.id, category.id, brand.id
            store.tenant_id, godown.tenant_id = tenant.id, tenant.id
            other_store.tenant_id = other_tenant.id
            second_store = Store(tenant_id=tenant.id, name="Second Store")
            second_godown = Godown(tenant_id=tenant.id, name="Second Godown")
            inactive_store = Store(
                tenant_id=tenant.id, name="Inactive Store", is_active=False
            )
            inactive_godown = Godown(
                tenant_id=tenant.id, name="Inactive Godown", is_active=False
            )
            other_godown = Godown(tenant_id=other_tenant.id, name="Other Godown")
            other_product = Product(
                tenant_id=other_tenant.id,
                category_id=category.id,
                brand_id=brand.id,
                sku="OTHER-1",
                name="Other Tenant Product",
            )
            inactive_product = Product(
                tenant_id=tenant.id,
                category_id=category.id,
                brand_id=brand.id,
                sku="INACTIVE-1",
                name="Inactive Product",
                is_active=False,
            )
            session.add_all(
                [
                    product,
                    store,
                    godown,
                    other_store,
                    second_store,
                    second_godown,
                    inactive_store,
                    inactive_godown,
                    other_godown,
                    other_product,
                    inactive_product,
                    supplier,
                    inactive_supplier,
                    other_supplier,
                ]
            )
            session.commit()
            self.tenant_id = tenant.id
            self.other_tenant_id = other_tenant.id
            self.product_id = product.id
            self.store_id = store.id
            self.godown_id = godown.id
            self.other_store_id = other_store.id
            self.second_store_id = second_store.id
            self.second_godown_id = second_godown.id
            self.inactive_store_id = inactive_store.id
            self.inactive_godown_id = inactive_godown.id
            self.other_godown_id = other_godown.id
            self.other_product_id = other_product.id
            self.inactive_product_id = inactive_product.id
            self.supplier_id = supplier.id
            self.inactive_supplier_id = inactive_supplier.id
            self.other_supplier_id = other_supplier.id

    def opening(self, **values):
        payload = {
            "product_id": self.product_id,
            "supplier_id": self.supplier_id,
            "store_id": self.store_id,
            "quantity": 5,
        }
        payload.update(values)
        return OpeningStockCreate(**payload)

    def create(self, request=None, service=None, tenant_id=None):
        with Session(self.engine) as session:
            return (service or InventoryService()).create_opening_stock(session, tenant_id or self.tenant_id, request or self.opening()).id

    def transfer_request(self, **overrides):
        payload = {
            "product_id": self.product_id,
            "source_store_id": self.store_id,
            "destination_store_id": self.second_store_id,
            "quantity": 5,
        }
        payload.update(overrides)
        return InventoryTransferCreate(**payload)

    def add_balance(
        self,
        *,
        product_id=None,
        tenant_id=None,
        store_id=None,
        godown_id=None,
        quantity=20,
        reserved_quantity=2,
    ):
        with Session(self.engine) as session:
            inventory = Inventory(
                tenant_id=tenant_id or self.tenant_id,
                product_id=product_id or self.product_id,
                store_id=store_id,
                godown_id=godown_id,
                quantity=quantity,
                reserved_quantity=reserved_quantity,
            )
            session.add(inventory)
            session.commit()
            return inventory.id

    def transfer(self, request=None, service=None):
        with Session(self.engine) as session:
            destination = (service or InventoryService()).transfer_inventory(
                session, self.tenant_id, request or self.transfer_request()
            )
            return destination.id

    def test_valid_store_opening(self):
        inventory_id = self.create()
        with Session(self.engine) as session:
            inventory = session.get(Inventory, inventory_id)
            self.assertEqual(inventory.quantity, 5)
            self.assertIsNone(inventory.godown_id)

    def test_valid_godown_opening(self):
        inventory_id = self.create(self.opening(store_id=None, godown_id=self.godown_id))
        self.assertIsNotNone(inventory_id)

    def test_zero_and_negative_quantity_rejected(self):
        with self.assertRaises(ValueError): OpeningStockCreate(**self.opening(quantity=0).model_dump())
        with self.assertRaises(ValueError): OpeningStockCreate(**self.opening(quantity=-1).model_dump())

    def test_supplier_id_is_required(self):
        with self.assertRaises(ValidationError):
            OpeningStockCreate(
                product_id=self.product_id, store_id=self.store_id, quantity=5
            )

    def test_invalid_supplier_id_rejected(self):
        with self.assertRaises(InventoryValidationError):
            self.create(self.opening(supplier_id=999))

    def test_inactive_supplier_rejected(self):
        with self.assertRaises(InventoryValidationError):
            self.create(self.opening(supplier_id=self.inactive_supplier_id))

    def test_other_tenant_supplier_rejected(self):
        with self.assertRaises(InventoryValidationError):
            self.create(self.opening(supplier_id=self.other_supplier_id))

    def test_both_or_neither_location_rejected(self):
        with self.assertRaises(InventoryValidationError): self.create(self.opening(godown_id=self.godown_id))
        with self.assertRaises(InventoryValidationError): self.create(self.opening(store_id=None))

    def test_invalid_product_store_and_godown_rejected(self):
        with self.assertRaises(InventoryValidationError): self.create(self.opening(product_id=999))
        with self.assertRaises(InventoryValidationError): self.create(self.opening(store_id=999))
        with self.assertRaises(InventoryValidationError): self.create(self.opening(store_id=None, godown_id=999))

    def test_duplicate_balance_rejected(self):
        self.create()
        with self.assertRaises(InventoryValidationError): self.create()

    def test_movement_created(self):
        self.create()
        with Session(self.engine) as session:
            movement = session.scalar(select(InventoryMovement))
            self.assertEqual(movement.movement_type, "OPENING")
            self.assertEqual(movement.quantity, 5)
            self.assertEqual(movement.supplier_id, self.supplier_id)

    def test_transaction_rolls_back(self):
        service = InventoryService()
        service.repository = FailingMovementRepository(service)
        with self.assertRaises(RuntimeError): self.create(service=service)
        with Session(self.engine) as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(Inventory)), 0)
            self.assertEqual(session.scalar(select(func.count()).select_from(InventoryMovement)), 0)

    def test_tenant_isolation(self):
        with self.assertRaises(InventoryValidationError): self.create(self.opening(store_id=self.other_store_id), tenant_id=self.tenant_id)
        with self.assertRaises(InventoryValidationError): self.create(self.opening(), tenant_id=self.other_tenant_id)

    def test_valid_store_to_store_transfer_updates_both_balances(self):
        source_id = self.add_balance(store_id=self.store_id)
        self.transfer()
        with Session(self.engine) as session:
            source = session.get(Inventory, source_id)
            destination = session.scalar(
                select(Inventory).where(Inventory.store_id == self.second_store_id)
            )
            self.assertEqual((source.quantity, source.reserved_quantity), (15, 2))
            self.assertEqual((destination.quantity, destination.reserved_quantity), (5, 0))

    def test_valid_store_to_godown_transfer(self):
        self.add_balance(store_id=self.store_id)
        self.transfer(
            self.transfer_request(
                destination_store_id=None,
                destination_godown_id=self.godown_id,
            )
        )
        with Session(self.engine) as session:
            destination = session.scalar(
                select(Inventory).where(Inventory.godown_id == self.godown_id)
            )
            self.assertEqual(destination.quantity, 5)

    def test_valid_godown_to_store_transfer(self):
        self.add_balance(godown_id=self.godown_id)
        self.transfer(
            self.transfer_request(
                source_store_id=None,
                source_godown_id=self.godown_id,
                destination_store_id=self.store_id,
            )
        )
        with Session(self.engine) as session:
            destination = session.scalar(
                select(Inventory).where(Inventory.store_id == self.store_id)
            )
            self.assertEqual(destination.quantity, 5)

    def test_valid_godown_to_godown_transfer(self):
        self.add_balance(godown_id=self.godown_id)
        self.transfer(
            self.transfer_request(
                source_store_id=None,
                source_godown_id=self.godown_id,
                destination_store_id=None,
                destination_godown_id=self.second_godown_id,
            )
        )
        with Session(self.engine) as session:
            destination = session.scalar(
                select(Inventory).where(
                    Inventory.godown_id == self.second_godown_id
                )
            )
            self.assertEqual(destination.quantity, 5)

    def test_existing_destination_quantity_increases_and_reserved_is_preserved(self):
        self.add_balance(store_id=self.store_id)
        destination_id = self.add_balance(
            store_id=self.second_store_id, quantity=8, reserved_quantity=3
        )
        self.transfer()
        with Session(self.engine) as session:
            destination = session.get(Inventory, destination_id)
            self.assertEqual((destination.quantity, destination.reserved_quantity), (13, 3))

    def test_transfer_cannot_exceed_available_quantity(self):
        self.add_balance(store_id=self.store_id, quantity=20, reserved_quantity=2)
        with self.assertRaises(InventoryValidationError):
            self.transfer(self.transfer_request(quantity=19))

    def test_transfer_rejects_missing_source_inventory(self):
        with self.assertRaises(InventoryValidationError):
            self.transfer()

    def test_transfer_rejects_same_source_and_destination(self):
        with self.assertRaises(InventoryValidationError):
            self.transfer(
                self.transfer_request(destination_store_id=self.store_id)
            )
        with self.assertRaises(InventoryValidationError):
            self.transfer(
                self.transfer_request(
                    source_store_id=None,
                    source_godown_id=self.godown_id,
                    destination_store_id=None,
                    destination_godown_id=self.godown_id,
                )
            )

    def test_transfer_schema_rejects_both_or_missing_source_locations(self):
        with self.assertRaises(ValidationError):
            self.transfer_request(source_godown_id=self.godown_id)
        with self.assertRaises(ValidationError):
            self.transfer_request(source_store_id=None, source_godown_id=None)

    def test_transfer_schema_rejects_both_or_missing_destination_locations(self):
        with self.assertRaises(ValidationError):
            self.transfer_request(destination_godown_id=self.godown_id)
        with self.assertRaises(ValidationError):
            self.transfer_request(
                destination_store_id=None, destination_godown_id=None
            )

    def test_transfer_schema_requires_positive_quantity(self):
        with self.assertRaises(ValidationError):
            self.transfer_request(quantity=0)
        with self.assertRaises(ValidationError):
            self.transfer_request(quantity=-1)

    def test_transfer_rejects_invalid_or_cross_tenant_product(self):
        with self.assertRaises(InventoryValidationError):
            self.transfer(self.transfer_request(product_id=999))
        with self.assertRaises(InventoryValidationError):
            self.transfer(
                self.transfer_request(product_id=self.other_product_id)
            )

    def test_transfer_rejects_inactive_product(self):
        with self.assertRaises(InventoryValidationError):
            self.transfer(
                self.transfer_request(product_id=self.inactive_product_id)
            )

    def test_transfer_rejects_cross_tenant_source_and_destination_locations(self):
        with self.assertRaises(InventoryValidationError):
            self.transfer(
                self.transfer_request(source_store_id=self.other_store_id)
            )
        self.add_balance(store_id=self.store_id)
        with self.assertRaises(InventoryValidationError):
            self.transfer(
                self.transfer_request(destination_store_id=self.other_store_id)
            )
        with self.assertRaises(InventoryValidationError):
            self.transfer(
                self.transfer_request(
                    source_store_id=None,
                    source_godown_id=self.other_godown_id,
                )
            )

    def test_transfer_rejects_inactive_source_and_destination_locations(self):
        with self.assertRaises(InventoryValidationError):
            self.transfer(
                self.transfer_request(source_store_id=self.inactive_store_id)
            )
        with self.assertRaises(InventoryValidationError):
            self.transfer(
                self.transfer_request(destination_store_id=self.inactive_store_id)
            )
        with self.assertRaises(InventoryValidationError):
            self.transfer(
                self.transfer_request(
                    source_store_id=None,
                    source_godown_id=self.inactive_godown_id,
                )
            )
        with self.assertRaises(InventoryValidationError):
            self.transfer(
                self.transfer_request(
                    destination_store_id=None,
                    destination_godown_id=self.inactive_godown_id,
                )
            )

    def test_transfer_creates_exactly_one_movement_without_supplier(self):
        self.add_balance(store_id=self.store_id)
        self.transfer()
        with Session(self.engine) as session:
            movements = list(session.scalars(select(InventoryMovement)))
            self.assertEqual(len(movements), 1)
            movement = movements[0]
            self.assertEqual(movement.movement_type, "TRANSFER")
            self.assertEqual(movement.product_id, self.product_id)
            self.assertEqual(movement.quantity, 5)
            self.assertEqual(movement.from_store_id, self.store_id)
            self.assertIsNone(movement.from_godown_id)
            self.assertEqual(movement.to_store_id, self.second_store_id)
            self.assertIsNone(movement.to_godown_id)
            self.assertIsNone(movement.supplier_id)

    def test_transfer_rolls_back_balances_when_movement_creation_fails(self):
        source_id = self.add_balance(store_id=self.store_id)
        destination_id = self.add_balance(
            store_id=self.second_store_id, quantity=8, reserved_quantity=1
        )
        service = InventoryService()
        service.repository = FailingMovementRepository(service)
        with self.assertRaises(RuntimeError):
            self.transfer(service=service)
        with Session(self.engine) as session:
            source = session.get(Inventory, source_id)
            destination = session.get(Inventory, destination_id)
            self.assertEqual((source.quantity, source.reserved_quantity), (20, 2))
            self.assertEqual((destination.quantity, destination.reserved_quantity), (8, 1))
            self.assertEqual(
                session.scalar(select(func.count()).select_from(InventoryMovement)),
                0,
            )

    def test_transfer_schema_rejects_tenant_id(self):
        with self.assertRaises(ValidationError):
            self.transfer_request(tenant_id=self.tenant_id)


if __name__ == "__main__":
    unittest.main()