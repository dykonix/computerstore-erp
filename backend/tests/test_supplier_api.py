import unittest

from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from pydantic import ValidationError

from app.api.routes.suppliers import (
    create_supplier,
    get_supplier,
    list_suppliers,
    update_supplier,
)
from app.database.base import Base
from app.models.supplier import Supplier
from app.models.tenant import Tenant
from app.schemas.supplier import SupplierCreate, SupplierUpdate
from app.services.supplier_service import SupplierService
from main import app


class SupplierAPITests(unittest.TestCase):
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
            tenant = Tenant(name="Tenant")
            other_tenant = Tenant(name="Other Tenant")
            session.add_all([tenant, other_tenant])
            session.commit()
            self.tenant_id = tenant.id
            self.other_tenant_id = other_tenant.id

    def payload(self, **overrides):
        values = {
            "name": "Acme Components",
            "contact_person": "Morgan Lee",
            "phone": "555-0100",
            "email": "orders@acme.example",
            "address": "10 Market Street",
            "is_active": True,
        }
        values.update(overrides)
        return SupplierCreate(**values)

    def create(self, tenant_id=None, request=None):
        with Session(self.engine) as session:
            return create_supplier(
                request or self.payload(),
                session,
                tenant_id or self.tenant_id,
                SupplierService(),
            )

    def test_create_valid_supplier(self):
        response = self.create()
        self.assertEqual(response.name, "Acme Components")
        self.assertEqual(response.contact_person, "Morgan Lee")
        self.assertEqual(response.phone, "555-0100")
        self.assertEqual(response.email, "orders@acme.example")
        self.assertEqual(response.address, "10 Market Street")
        self.assertTrue(response.is_active)
        self.assertFalse(hasattr(response, "tenant_id"))
        with Session(self.engine) as session:
            saved = session.get(Supplier, response.id)
            self.assertEqual(saved.tenant_id, self.tenant_id)

    def test_supplier_name_is_required(self):
        with self.assertRaises(ValidationError):
            SupplierCreate()
        with self.assertRaises(HTTPException) as context:
            self.create(request=self.payload(name="   "))
        self.assertEqual(context.exception.status_code, 400)

    def test_get_supplier(self):
        created = self.create()
        with Session(self.engine) as session:
            response = get_supplier(
                created.id, session, self.tenant_id, SupplierService()
            )
        self.assertEqual(response.id, created.id)
        self.assertEqual(response.name, "Acme Components")

    def test_list_suppliers_only_returns_current_tenant(self):
        self.create()
        self.create(tenant_id=self.other_tenant_id, request=self.payload(name="Other"))
        with Session(self.engine) as session:
            response = list_suppliers(
                page=1,
                page_size=20,
                is_active=None,
                session=session,
                tenant_id=self.tenant_id,
                service=SupplierService(),
            )
        self.assertEqual(response.total, 1)
        self.assertEqual([item.name for item in response.items], ["Acme Components"])

    def test_update_supplier(self):
        created = self.create()
        request = SupplierUpdate(name="Acme Updated", phone="555-0199")
        with Session(self.engine) as session:
            response = update_supplier(
                created.id, request, session, self.tenant_id, SupplierService()
            )
        self.assertEqual(response.name, "Acme Updated")
        self.assertEqual(response.phone, "555-0199")
        self.assertEqual(response.email, "orders@acme.example")

    def test_deactivate_supplier_with_update(self):
        created = self.create()
        with Session(self.engine) as session:
            response = update_supplier(
                created.id,
                SupplierUpdate(is_active=False),
                session,
                self.tenant_id,
                SupplierService(),
            )
        self.assertFalse(response.is_active)
        with Session(self.engine) as session:
            inactive = list_suppliers(
                page=1,
                page_size=20,
                is_active=False,
                session=session,
                tenant_id=self.tenant_id,
                service=SupplierService(),
            )
        self.assertEqual(inactive.total, 1)
        self.assertFalse(inactive.items[0].is_active)

    def test_null_activation_state_is_rejected(self):
        created = self.create()
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as context:
                update_supplier(
                    created.id,
                    SupplierUpdate(is_active=None),
                    session,
                    self.tenant_id,
                    SupplierService(),
                )
        self.assertEqual(context.exception.status_code, 400)

    def test_other_tenant_supplier_cannot_be_accessed_or_updated(self):
        created = self.create(tenant_id=self.other_tenant_id)
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as get_context:
                get_supplier(created.id, session, self.tenant_id, SupplierService())
        self.assertEqual(get_context.exception.status_code, 404)
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as update_context:
                update_supplier(
                    created.id,
                    SupplierUpdate(name="Should not update"),
                    session,
                    self.tenant_id,
                    SupplierService(),
                )
        self.assertEqual(update_context.exception.status_code, 404)
        with Session(self.engine) as session:
            supplier = session.scalar(select(Supplier).where(Supplier.id == created.id))
            self.assertEqual(supplier.name, "Acme Components")

    def test_tenant_id_is_rejected_from_create_and_update(self):
        with self.assertRaises(ValidationError):
            SupplierCreate(name="Acme", tenant_id=self.tenant_id)
        with self.assertRaises(ValidationError):
            SupplierUpdate(tenant_id=self.other_tenant_id)

    def test_router_exposes_only_supplier_master_operations(self):
        supplier_routes = {
            (path, tuple(sorted(method.upper() for method in operations)))
            for path, operations in app.openapi()["paths"].items()
            if path.startswith("/suppliers")
        }
        self.assertEqual(
            supplier_routes,
            {
                ("/suppliers", ("GET", "POST")),
                ("/suppliers/{supplier_id}", ("GET", "PUT")),
            },
        )


if __name__ == "__main__":
    unittest.main()