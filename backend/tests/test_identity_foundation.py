import unittest

from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.models.employee import Employee
from app.models.employee_store import EmployeeStore
from app.models.store import Store
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.employee_store import EmployeeStoreAssignmentCreate
from app.schemas.user import UserIdentityCreate, UserIdentityUpdate
from app.services.employee_store_service import (
    EmployeeStoreAssignmentError,
    EmployeeStoreService,
)
from app.services.user_service import UserIdentityError, UserIdentityService
from app.services.user_service import UserNotFoundError


class IdentityFoundationTests(unittest.TestCase):
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
            session.add_all([tenant_a, tenant_b])
            session.flush()
            employee_a = Employee(
                tenant_id=tenant_a.id, email="employee-a@example.com", name="A"
            )
            employee_b = Employee(
                tenant_id=tenant_b.id, email="employee-b@example.com", name="B"
            )
            inactive_employee = Employee(
                tenant_id=tenant_a.id,
                email="inactive@example.com",
                name="Inactive",
                is_active=False,
            )
            store_a = Store(tenant_id=tenant_a.id, name="Store A")
            store_a2 = Store(tenant_id=tenant_a.id, name="Store A2")
            store_b = Store(tenant_id=tenant_b.id, name="Store B")
            inactive_store = Store(
                tenant_id=tenant_a.id, name="Inactive Store", is_active=False
            )
            session.add_all(
                [employee_a, employee_b, inactive_employee, store_a, store_a2, store_b, inactive_store]
            )
            session.commit()
            self.tenant_a_id = tenant_a.id
            self.tenant_b_id = tenant_b.id
            self.employee_a_id = employee_a.id
            self.employee_b_id = employee_b.id
            self.inactive_employee_id = inactive_employee.id
            self.store_a_id = store_a.id
            self.store_a2_id = store_a2.id
            self.store_b_id = store_b.id
            self.inactive_store_id = inactive_store.id

    def user_request(self, **overrides):
        fields = {
            "username": "sales-user",
            "email": "  Sales.User@Example.COM  ",
            "mobile": "+1 (555) 123-4567",
            "employee_id": self.employee_a_id,
        }
        fields.update(overrides)
        return UserIdentityCreate(**fields)

    def create_user(self, tenant_id=None, request=None):
        with Session(self.engine) as session:
            user = UserIdentityService().create_user(
                session,
                tenant_id or self.tenant_a_id,
                request or self.user_request(),
                password_hash="test-only-hash",
            )
            return user.id

    def assign(self, tenant_id, employee_id, store_id):
        with Session(self.engine) as session:
            EmployeeStoreService().assign_store(
                session,
                tenant_id,
                EmployeeStoreAssignmentCreate(
                    employee_id=employee_id, store_id=store_id
                ),
            )
            return employee_id, store_id

    def test_valid_user_identity_is_stored_canonically(self):
        user_id = self.create_user()
        with Session(self.engine) as session:
            user = session.get(User, user_id)
            self.assertEqual(user.email, "sales.user@example.com")
            self.assertEqual(user.mobile, "+15551234567")
            self.assertEqual(user.tenant_id, self.tenant_a_id)
            self.assertEqual(user.employee_id, self.employee_a_id)

    def test_mobile_normalization_preserves_optional_plus_without_country_guessing(self):
        user_id = self.create_user(
            request=self.user_request(
                email="local@example.com",
                mobile=" (555) 123-4567 ",
                employee_id=None,
            )
        )
        with Session(self.engine) as session:
            self.assertEqual(session.get(User, user_id).mobile, "5551234567")

    def test_blank_or_invalid_email_and_mobile_are_rejected(self):
        for email in (
            "",
            "   ",
            "not-an-email",
            ".user@example.com",
            "user..name@example.com",
            "user@..example.com",
        ):
            with self.subTest(email=email), self.assertRaises(UserIdentityError):
                self.create_user(request=self.user_request(email=email))
        for mobile in ("", "   ", "++15551234567", "123-ABC"):
            with self.subTest(mobile=mobile), self.assertRaises(UserIdentityError):
                self.create_user(request=self.user_request(mobile=mobile))

    def test_global_duplicate_email_is_rejected_across_tenants(self):
        self.create_user()
        with self.assertRaises(UserIdentityError):
            self.create_user(
                self.tenant_b_id,
                self.user_request(
                    email="sales.user@example.com",
                    mobile="+1 555 987 6543",
                    employee_id=None,
                ),
            )

    def test_global_duplicate_mobile_is_rejected_across_tenants(self):
        self.create_user()
        with self.assertRaises(UserIdentityError):
            self.create_user(
                self.tenant_b_id,
                self.user_request(
                    email="different@example.com",
                    mobile="+1-555-123-4567",
                    employee_id=None,
                ),
            )

    def test_employee_can_be_associated_with_at_most_one_user(self):
        self.create_user()
        with self.assertRaises(UserIdentityError):
            self.create_user(
                request=self.user_request(
                    email="second@example.com", mobile="5559876543"
                )
            )

    def test_nonexistent_employee_is_rejected(self):
        with self.assertRaises(UserIdentityError):
            self.create_user(request=self.user_request(employee_id=9999))

    def test_cross_tenant_employee_is_rejected(self):
        with self.assertRaises(UserIdentityError):
            self.create_user(
                request=self.user_request(employee_id=self.employee_b_id)
            )

    def test_tenant_cannot_be_supplied_or_changed_through_identity_schema(self):
        with self.assertRaises(ValidationError):
            self.user_request(tenant_id=self.tenant_b_id)
        with self.assertRaises(ValidationError):
            UserIdentityUpdate(tenant_id=self.tenant_b_id)

    def test_wrong_tenant_cannot_update_another_tenants_user(self):
        user_id = self.create_user(self.tenant_b_id, self.user_request(employee_id=None))
        with Session(self.engine) as session:
            with self.assertRaises(UserNotFoundError) as context:
                UserIdentityService().update_user(
                    session,
                    self.tenant_a_id,
                    user_id,
                    UserIdentityUpdate(email="changed@example.com"),
                )
        self.assertEqual(str(context.exception), "User not found")
        with Session(self.engine) as session:
            unchanged = session.scalar(select(User).where(User.id == user_id))
            self.assertEqual(unchanged.email, "sales.user@example.com")

    def test_update_normalizes_identity_and_keeps_tenant_unchanged(self):
        user_id = self.create_user()
        with Session(self.engine) as session:
            updated = UserIdentityService().update_user(
                session,
                self.tenant_a_id,
            user_id,
                UserIdentityUpdate(
                    email=" New.Email@Example.COM ", mobile="(555) 000-1234"
                ),
            )
            self.assertEqual(updated.email, "new.email@example.com")
            self.assertEqual(updated.mobile, "5550001234")
            self.assertEqual(updated.tenant_id, self.tenant_a_id)

    def test_update_rejects_duplicate_email_and_mobile_globally(self):
        self.create_user()
        second_id = self.create_user(
            request=self.user_request(
                email="second@example.com",
                mobile="5559876543",
                employee_id=None,
            )
        )
        service = UserIdentityService()
        with Session(self.engine) as session:
            with self.assertRaises(UserIdentityError):
                service.update_user(
                    session,
                    self.tenant_a_id,
                    second_id,
                    UserIdentityUpdate(email="sales.user@example.com"),
                )
        with Session(self.engine) as session:
            with self.assertRaises(UserIdentityError):
                service.update_user(
                    session,
                    self.tenant_a_id,
                    second_id,
                    UserIdentityUpdate(mobile="+1 (555) 123-4567"),
                )

    def test_assign_employee_to_one_store(self):
        assignment = self.assign(
            self.tenant_a_id, self.employee_a_id, self.store_a_id
        )
        self.assertEqual(assignment, (self.employee_a_id, self.store_a_id))

    def test_assign_employee_to_multiple_stores(self):
        service = EmployeeStoreService()
        with Session(self.engine) as session:
            service.assign_store(
                session,
                self.tenant_a_id,
                EmployeeStoreAssignmentCreate(
                    employee_id=self.employee_a_id, store_id=self.store_a_id
                ),
            )
        with Session(self.engine) as session:
            service.assign_store(
                session,
                self.tenant_a_id,
                EmployeeStoreAssignmentCreate(
                    employee_id=self.employee_a_id, store_id=self.store_a2_id
                ),
            )
        with Session(self.engine) as session:
            stores = service.list_stores(session, self.tenant_a_id, self.employee_a_id)
        self.assertEqual({store.id for store in stores}, {self.store_a_id, self.store_a2_id})

    def test_duplicate_assignment_is_rejected_by_service_and_database(self):
        self.assign(self.tenant_a_id, self.employee_a_id, self.store_a_id)
        with self.assertRaises(EmployeeStoreAssignmentError):
            self.assign(self.tenant_a_id, self.employee_a_id, self.store_a_id)
        with Session(self.engine) as session:
            session.add(
                EmployeeStore(
                    employee_id=self.employee_a_id, store_id=self.store_a_id
                )
            )
            with self.assertRaises(IntegrityError):
                session.flush()
            session.rollback()

    def test_cross_tenant_employee_assignment_is_rejected(self):
        with self.assertRaises(EmployeeStoreAssignmentError):
            self.assign(self.tenant_a_id, self.employee_b_id, self.store_a_id)

    def test_cross_tenant_store_assignment_is_rejected(self):
        with self.assertRaises(EmployeeStoreAssignmentError):
            self.assign(self.tenant_a_id, self.employee_a_id, self.store_b_id)

    def test_missing_employee_or_store_assignment_is_rejected(self):
        with self.assertRaises(EmployeeStoreAssignmentError):
            self.assign(self.tenant_a_id, 9999, self.store_a_id)
        with self.assertRaises(EmployeeStoreAssignmentError):
            self.assign(self.tenant_a_id, self.employee_a_id, 9999)

    def test_inactive_employee_assignment_is_rejected(self):
        with self.assertRaises(EmployeeStoreAssignmentError):
            self.assign(self.tenant_a_id, self.inactive_employee_id, self.store_a_id)

    def test_inactive_store_assignment_is_rejected(self):
        with self.assertRaises(EmployeeStoreAssignmentError):
            self.assign(self.tenant_a_id, self.employee_a_id, self.inactive_store_id)

    def test_assignment_schema_rejects_tenant_id(self):
        with self.assertRaises(ValidationError):
            EmployeeStoreAssignmentCreate(
                employee_id=self.employee_a_id,
                store_id=self.store_a_id,
                tenant_id=self.tenant_a_id,
            )

    def test_tenant_isolation_for_assignment_listing_and_removal(self):
        self.assign(self.tenant_b_id, self.employee_b_id, self.store_b_id)
        service = EmployeeStoreService()
        with Session(self.engine) as session:
            with self.assertRaises(EmployeeStoreAssignmentError):
                service.list_stores(session, self.tenant_a_id, self.employee_b_id)
        with Session(self.engine) as session:
            with self.assertRaises(EmployeeStoreAssignmentError):
                service.remove_store(
                    session,
                    self.tenant_a_id,
                    self.employee_b_id,
                    self.store_b_id,
                )

    def test_remove_assignment(self):
        self.assign(self.tenant_a_id, self.employee_a_id, self.store_a_id)
        with Session(self.engine) as session:
            EmployeeStoreService().remove_store(
                session,
                self.tenant_a_id,
                self.employee_a_id,
                self.store_a_id,
            )
        with Session(self.engine) as session:
            self.assertIsNone(
                session.get(
                    EmployeeStore,
                    {"employee_id": self.employee_a_id, "store_id": self.store_a_id},
                )
            )


if __name__ == "__main__":
    unittest.main()