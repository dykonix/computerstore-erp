import unittest

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.models.brand import Brand
from app.models.category import Category
from app.models.product import Product
from app.models.product_serial_number import ProductSerialNumber
from app.models.tenant import Tenant
from app.repositories.product_serial_number_repository import (
    ProductSerialNumberRepository,
)


class ProductSerialNumberRepositoryTests(unittest.TestCase):
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
            tenant_a = Tenant(name="Tenant A")
            tenant_b = Tenant(name="Tenant B")

            category = Category(name="Laptops")
            brand = Brand(name="HP")

            session.add_all(
                [
                    tenant_a,
                    tenant_b,
                    category,
                    brand,
                ]
            )
            session.flush()

            product_a = Product(
                tenant_id=tenant_a.id,
                category_id=category.id,
                brand_id=brand.id,
                sku="HP-A-001",
                name="HP Laptop A",
                is_active=True,
            )

            product_a2 = Product(
                tenant_id=tenant_a.id,
                category_id=category.id,
                brand_id=brand.id,
                sku="HP-A-002",
                name="HP Laptop B",
                is_active=True,
            )

            product_b = Product(
                tenant_id=tenant_b.id,
                category_id=category.id,
                brand_id=brand.id,
                sku="HP-B-001",
                name="HP Laptop Tenant B",
                is_active=True,
            )

            session.add_all(
                [
                    product_a,
                    product_a2,
                    product_b,
                ]
            )
            session.commit()

            self.tenant_a_id = tenant_a.id
            self.tenant_b_id = tenant_b.id

            self.product_a_id = product_a.id
            self.product_a2_id = product_a2.id
            self.product_b_id = product_b.id

    def test_create_serial_number(self):
        repository = ProductSerialNumberRepository()

        with Session(self.engine) as session:
            serial = ProductSerialNumber(
                tenant_id=self.tenant_a_id,
                product_id=self.product_a_id,
                serial_number="HP-SN-001",
                status="IN_STOCK",
            )

            result = repository.create(
                session,
                serial,
            )

            session.commit()

            self.assertIsNotNone(result.id)
            self.assertEqual(
                result.tenant_id,
                self.tenant_a_id,
            )
            self.assertEqual(
                result.product_id,
                self.product_a_id,
            )
            self.assertEqual(
                result.serial_number,
                "HP-SN-001",
            )
            self.assertEqual(
                result.status,
                "IN_STOCK",
            )

    def test_get_by_id_is_tenant_scoped(self):
        repository = ProductSerialNumberRepository()

        with Session(self.engine) as session:
            serial = ProductSerialNumber(
                tenant_id=self.tenant_a_id,
                product_id=self.product_a_id,
                serial_number="HP-SN-002",
                status="IN_STOCK",
            )

            session.add(serial)
            session.commit()

            serial_id = serial.id

        with Session(self.engine) as session:
            result = repository.get_by_id(
                session,
                self.tenant_a_id,
                serial_id,
            )

            self.assertIsNotNone(result)
            self.assertEqual(result.serial_number, "HP-SN-002")

            other_tenant_result = repository.get_by_id(
                session,
                self.tenant_b_id,
                serial_id,
            )

            self.assertIsNone(other_tenant_result)

    def test_get_by_serial_number_is_tenant_scoped(self):
        repository = ProductSerialNumberRepository()

        with Session(self.engine) as session:
            serial = ProductSerialNumber(
                tenant_id=self.tenant_a_id,
                product_id=self.product_a_id,
                serial_number="HP-SN-003",
                status="IN_STOCK",
            )

            session.add(serial)
            session.commit()

        with Session(self.engine) as session:
            result = repository.get_by_serial_number(
                session,
                self.tenant_a_id,
                "HP-SN-003",
            )

            self.assertIsNotNone(result)
            self.assertEqual(
                result.product_id,
                self.product_a_id,
            )

            other_tenant_result = (
                repository.get_by_serial_number(
                    session,
                    self.tenant_b_id,
                    "HP-SN-003",
                )
            )

            self.assertIsNone(other_tenant_result)

    def test_list_by_product_returns_all_product_serials(self):
        repository = ProductSerialNumberRepository()

        with Session(self.engine) as session:
            session.add_all(
                [
                    ProductSerialNumber(
                        tenant_id=self.tenant_a_id,
                        product_id=self.product_a_id,
                        serial_number="HP-SN-004",
                        status="IN_STOCK",
                    ),
                    ProductSerialNumber(
                        tenant_id=self.tenant_a_id,
                        product_id=self.product_a_id,
                        serial_number="HP-SN-005",
                        status="RESERVED",
                    ),
                    ProductSerialNumber(
                        tenant_id=self.tenant_a_id,
                        product_id=self.product_a2_id,
                        serial_number="HP-SN-006",
                        status="IN_STOCK",
                    ),
                ]
            )
            session.commit()

        with Session(self.engine) as session:
            result = repository.list_by_product(
                session,
                self.tenant_a_id,
                self.product_a_id,
            )

            self.assertEqual(len(result), 2)
            self.assertEqual(
                [item.serial_number for item in result],
                [
                    "HP-SN-004",
                    "HP-SN-005",
                ],
            )

    def test_list_by_product_can_filter_by_status(self):
        repository = ProductSerialNumberRepository()

        with Session(self.engine) as session:
            session.add_all(
                [
                    ProductSerialNumber(
                        tenant_id=self.tenant_a_id,
                        product_id=self.product_a_id,
                        serial_number="HP-SN-007",
                        status="IN_STOCK",
                    ),
                    ProductSerialNumber(
                        tenant_id=self.tenant_a_id,
                        product_id=self.product_a_id,
                        serial_number="HP-SN-008",
                        status="RESERVED",
                    ),
                    ProductSerialNumber(
                        tenant_id=self.tenant_a_id,
                        product_id=self.product_a_id,
                        serial_number="HP-SN-009",
                        status="SOLD",
                    ),
                ]
            )
            session.commit()

        with Session(self.engine) as session:
            result = repository.list_by_product(
                session,
                self.tenant_a_id,
                self.product_a_id,
                status="IN_STOCK",
            )

            self.assertEqual(len(result), 1)
            self.assertEqual(
                result[0].serial_number,
                "HP-SN-007",
            )

            result = repository.list_by_product(
                session,
                self.tenant_a_id,
                self.product_a_id,
                status="RESERVED",
            )

            self.assertEqual(len(result), 1)
            self.assertEqual(
                result[0].serial_number,
                "HP-SN-008",
            )

    def test_update_status(self):
        repository = ProductSerialNumberRepository()

        with Session(self.engine) as session:
            serial = ProductSerialNumber(
                tenant_id=self.tenant_a_id,
                product_id=self.product_a_id,
                serial_number="HP-SN-010",
                status="IN_STOCK",
            )

            session.add(serial)
            session.commit()

            result = repository.update_status(
                session,
                serial,
                "RESERVED",
            )

            session.commit()

            self.assertEqual(
                result.status,
                "RESERVED",
            )

    def test_duplicate_serial_number_is_rejected_within_tenant(self):
        repository = ProductSerialNumberRepository()

        with Session(self.engine) as session:
            session.add(
                ProductSerialNumber(
                    tenant_id=self.tenant_a_id,
                    product_id=self.product_a_id,
                    serial_number="HP-SN-011",
                    status="IN_STOCK",
                )
            )
            session.commit()

        with Session(self.engine) as session:
            session.add(
                ProductSerialNumber(
                    tenant_id=self.tenant_a_id,
                    product_id=self.product_a2_id,
                    serial_number="HP-SN-011",
                    status="IN_STOCK",
                )
            )

            with self.assertRaises(IntegrityError):
                session.commit()

            session.rollback()

    def test_same_serial_number_can_exist_in_different_tenants(self):
        repository = ProductSerialNumberRepository()

        with Session(self.engine) as session:
            first = ProductSerialNumber(
                tenant_id=self.tenant_a_id,
                product_id=self.product_a_id,
                serial_number="HP-SN-012",
                status="IN_STOCK",
            )

            second = ProductSerialNumber(
                tenant_id=self.tenant_b_id,
                product_id=self.product_b_id,
                serial_number="HP-SN-012",
                status="IN_STOCK",
            )

            repository.create(session, first)
            repository.create(session, second)

            session.commit()

            self.assertIsNotNone(first.id)
            self.assertIsNotNone(second.id)
            self.assertNotEqual(first.id, second.id)


if __name__ == "__main__":
    unittest.main()