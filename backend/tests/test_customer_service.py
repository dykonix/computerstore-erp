import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.models.customer import Customer
from app.models.tenant import Tenant
from app.services.customer_service import CustomerService


class CustomerServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            'sqlite://',
            connect_args={'check_same_thread': False},
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
            tenant_a = Tenant(name='Tenant A')
            tenant_b = Tenant(name='Tenant B')
            session.add_all([tenant_a, tenant_b])
            session.flush()

            session.add_all([
                Customer(
                    tenant_id=tenant_a.id,
                    name='Rahul Kumar',
                    mobile='9876543210',
                    email='rahul@example.com',
                    address='Delhi',
                ),
                Customer(
                    tenant_id=tenant_a.id,
                    name='Amit Kumar',
                    mobile='9812345678',
                    email='amit@example.com',
                    address='Noida',
                ),
                Customer(
                    tenant_id=tenant_b.id,
                    name='Other Tenant Customer',
                    mobile='9999999999',
                    email='other@example.com',
                    address='Bhopal',
                ),
            ])
            session.commit()

            self.tenant_a_id = tenant_a.id
            self.tenant_b_id = tenant_b.id

    def test_search_customers_filters_by_tenant_and_matches_mobile_or_name(self):
        service = CustomerService()

        with Session(self.engine) as session:
            matches = service.search_customers(
                session,
                tenant_id=self.tenant_a_id,
                query='98765',
            )

            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0].name, 'Rahul Kumar')
            self.assertEqual(matches[0].mobile, '9876543210')

            name_matches = service.search_customers(
                session,
                tenant_id=self.tenant_a_id,
                query='amit',
            )

            self.assertEqual(len(name_matches), 1)
            self.assertEqual(name_matches[0].name, 'Amit Kumar')

            cross_tenant = service.search_customers(
                session,
                tenant_id=self.tenant_a_id,
                query='Other Tenant',
            )

            self.assertEqual(cross_tenant, [])

    def test_create_customer_rejects_duplicate_mobile_within_tenant(self):
        service = CustomerService()

        with Session(self.engine) as session:
            with self.assertRaises(ValueError) as context:
                service.create_customer(
                    session,
                    tenant_id=self.tenant_a_id,
                    name='Rahul Duplicate',
                    mobile='9876543210',
                    email='duplicate@example.com',
                    address='New Delhi',
                )

            self.assertEqual(
                str(context.exception),
                'A customer with this mobile number already exists for this tenant',
            )

    def test_create_customer_creates_tenant_scoped_record(self):
        service = CustomerService()

        with Session(self.engine) as session:
            customer = service.create_customer(
                session,
                tenant_id=self.tenant_a_id,
                name='New Customer',
                mobile='9000000001',
                email='new@example.com',
                address='Gurugram',
            )

            session.commit()

            self.assertEqual(customer.tenant_id, self.tenant_a_id)
            self.assertEqual(customer.name, 'New Customer')
            self.assertEqual(customer.mobile, '9000000001')
            self.assertTrue(customer.is_active)


if __name__ == '__main__':
    unittest.main()
