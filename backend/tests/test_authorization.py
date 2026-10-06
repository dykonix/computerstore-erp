import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_user, require_permission
from app.api.routes.auth import get_authenticated_user
from app.database.base import Base
from app.models.employee import Employee
from app.models.employee_store import EmployeeStore
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.store import Store
from app.models.tenant import Tenant
from app.models.user import User
from app.models.user_role import UserRole
from app.security.jwt import create_access_token
from app.security.password import hash_password
from app.seed import seed_authorization
from app.services.authorization_service import (
    ALL_PERMISSION,
    ALL_TENANT_STORES,
    ASSIGNED_STORES,
    AuthorizationError,
    AuthorizationService,
    PermissionDeniedError,
)


TEST_SECRET = "authorization-test-secret-never-used-outside-tests-0123456789"


class AuthorizationTests(unittest.TestCase):
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
        self.environment = patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": TEST_SECRET,
                "JWT_ALGORITHM": "HS256",
                "JWT_ACCESS_TOKEN_EXPIRE_MINUTES": "15",
            },
        )
        self.environment.start()
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            self.tenant_a = Tenant(name="Tenant A")
            self.tenant_b = Tenant(name="Tenant B")
            session.add_all([self.tenant_a, self.tenant_b])
            session.flush()
            self.employee_a = Employee(
                tenant_id=self.tenant_a.id, email="employee-a@example.com", name="A"
            )
            self.employee_b = Employee(
                tenant_id=self.tenant_b.id, email="employee-b@example.com", name="B"
            )
            self.inactive_employee = Employee(
                tenant_id=self.tenant_a.id,
                email="inactive@example.com",
                name="Inactive",
                is_active=False,
            )
            self.store_a = Store(tenant_id=self.tenant_a.id, name="A Store")
            self.store_a2 = Store(tenant_id=self.tenant_a.id, name="A Store 2")
            self.store_b = Store(tenant_id=self.tenant_b.id, name="B Store")
            self.inactive_store = Store(
                tenant_id=self.tenant_a.id, name="Inactive Store", is_active=False
            )
            self.sell = Permission(code="sell")
            self.all_permission = Permission(code=ALL_PERMISSION)
            session.add_all(
                [
                    self.employee_a,
                    self.employee_b,
                    self.inactive_employee,
                    self.store_a,
                    self.store_a2,
                    self.store_b,
                    self.inactive_store,
                    self.sell,
                    self.all_permission,
                ]
            )
            session.flush()
            self.assigned_role = Role(
                tenant_id=self.tenant_a.id, name="Sales", is_active=True
            )
            self.global_role = Role(
                tenant_id=self.tenant_a.id, name="Sales Global", is_active=True
            )
            self.inactive_role = Role(
                tenant_id=self.tenant_a.id, name="Inactive Role", is_active=False
            )
            self.cross_tenant_role = Role(
                tenant_id=self.tenant_b.id, name="Other Tenant Sales", is_active=True
            )
            session.add_all(
                [self.assigned_role, self.global_role, self.inactive_role, self.cross_tenant_role]
            )
            session.flush()
            self.user = self.make_user(self.tenant_a.id, self.employee_a.id)
            self.user_no_employee = self.make_user(
                self.tenant_a.id, None, "no-employee@example.com"
            )
            self.user_b = self.make_user(
                self.tenant_b.id, self.employee_b.id, "tenant-b@example.com"
            )
            session.add_all([self.user, self.user_no_employee, self.user_b])
            session.flush()
            session.add_all(
                [
                    RolePermission(
                        role_id=self.assigned_role.id,
                        permission_id=self.sell.id,
                        scope=ASSIGNED_STORES,
                    ),
                    RolePermission(
                        role_id=self.global_role.id,
                        permission_id=self.sell.id,
                        scope=ALL_TENANT_STORES,
                    ),
                    RolePermission(
                        role_id=self.inactive_role.id,
                        permission_id=self.sell.id,
                        scope=ALL_TENANT_STORES,
                    ),
                    RolePermission(
                        role_id=self.cross_tenant_role.id,
                        permission_id=self.sell.id,
                        scope=ALL_TENANT_STORES,
                    ),
                ]
            )
            session.add(
                EmployeeStore(
                    employee_id=self.employee_a.id, store_id=self.store_a.id
                )
            )
            session.commit()
            self.tenant_a_id = self.tenant_a.id
            self.tenant_b_id = self.tenant_b.id
            self.employee_a_id = self.employee_a.id
            self.employee_b_id = self.employee_b.id
            self.inactive_employee_id = self.inactive_employee.id
            self.store_a_id = self.store_a.id
            self.store_a2_id = self.store_a2.id
            self.store_b_id = self.store_b.id
            self.inactive_store_id = self.inactive_store.id
            self.sell_id = self.sell.id
            self.all_permission_id = self.all_permission.id
            self.assigned_role_id = self.assigned_role.id
            self.global_role_id = self.global_role.id
            self.inactive_role_id = self.inactive_role.id
            self.cross_tenant_role_id = self.cross_tenant_role.id
            self.user_id = self.user.id
            self.user_no_employee_id = self.user_no_employee.id
            self.user_b_id = self.user_b.id

    def tearDown(self):
        self.environment.stop()

    @staticmethod
    def make_user(tenant_id, employee_id, email="sales@example.com"):
        return User(
            tenant_id=tenant_id,
            username=email.split("@")[0],
            password_hash=hash_password("authorization-test-password"),
            email=email,
            mobile=f"+1555{abs(hash(email)) % 10000000:07d}",
            employee_id=employee_id,
            is_active=True,
        )

    def add_role(self, session, user_id, role_id):
        session.add(UserRole(user_id=user_id, role_id=role_id))
        session.flush()

    def test_unauthenticated_request_is_rejected(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as context:
                get_current_user(None, session)
        self.assertEqual(context.exception.status_code, 401)

    def test_auth_me_returns_effective_codes_without_password_hash(self):
        with Session(self.engine) as session:
            self.add_role(session, self.user_id, self.assigned_role_id)
            user = session.get(User, self.user_id)
            response = get_authenticated_user(user, session)
        self.assertEqual(response.permissions, ["sell"])
        self.assertEqual(response.id, self.user_id)
        self.assertFalse(hasattr(response, "password_hash"))

    def test_sell_permission_is_granted_from_active_role(self):
        service = AuthorizationService()
        with Session(self.engine) as session:
            self.add_role(session, self.user_id, self.assigned_role_id)
            user = session.get(User, self.user_id)
            service.require_permission(session, user, "sell")

    def test_user_without_permission_is_denied(self):
        with Session(self.engine) as session:
            user = session.get(User, self.user_id)
            with self.assertRaises(PermissionDeniedError):
                AuthorizationService().require_permission(session, user, "sell")

    def test_inactive_role_does_not_grant_permission(self):
        with Session(self.engine) as session:
            self.add_role(session, self.user_id, self.inactive_role_id)
            user = session.get(User, self.user_id)
            with self.assertRaises(PermissionDeniedError):
                AuthorizationService().require_permission(session, user, "sell")

    def test_cross_tenant_role_cannot_grant_permission(self):
        with Session(self.engine) as session:
            session.add(
                UserRole(user_id=self.user_id, role_id=self.cross_tenant_role_id)
            )
            session.flush()
            user = session.get(User, self.user_id)
            with self.assertRaises(PermissionDeniedError):
                AuthorizationService().require_permission(session, user, "sell")

    def test_all_permission_expands_effective_codes_and_respects_tenant(self):
        service = AuthorizationService()
        with Session(self.engine) as session:
            self.add_role(session, self.user_id, self.assigned_role_id)
            self.add_role(session, self.user_id, self.global_role_id)
            self.add_role(session, self.user_id, self.inactive_role_id)
            self.add_role(session, self.user_id, self.cross_tenant_role_id)
            session.add(
                RolePermission(
                    role_id=self.assigned_role_id,
                    permission_id=self.all_permission_id,
                    scope=ASSIGNED_STORES,
                )
            )
            session.flush()
            user = session.get(User, self.user_id)
            self.assertEqual(service.effective_permissions(session, user), ["sell"])
            service.require_permission(session, user, "sell", self.store_a2_id)
            with self.assertRaises(PermissionDeniedError):
                service.require_permission(session, user, "future.unknown.permission")
            with self.assertRaises(PermissionDeniedError):
                service.require_permission(session, user, "sell", self.store_b_id)

    def test_assigned_store_scope_allows_only_active_assigned_store(self):
        service = AuthorizationService()
        with Session(self.engine) as session:
            self.add_role(session, self.user_id, self.assigned_role_id)
            user = session.get(User, self.user_id)
            service.require_permission(session, user, "sell", self.store_a_id)
            for denied_store in (
                self.store_a2_id,
                self.store_b_id,
                self.inactive_store_id,
            ):
                with self.subTest(store_id=denied_store), self.assertRaises(
                    PermissionDeniedError
                ):
                    service.require_permission(session, user, "sell", denied_store)

    def test_assigned_store_scope_rejects_inactive_employee(self):
        with Session(self.engine) as session:
            user = self.make_user(
                self.tenant_a_id,
                self.inactive_employee_id,
                "inactive-user@example.com",
            )
            session.add(user)
            session.flush()
            self.add_role(session, user.id, self.global_role_id)
            with self.assertRaises(PermissionDeniedError):
                AuthorizationService().require_permission(
                    session, user, "sell", self.store_a_id
                )

    def test_all_tenant_store_scope_allows_active_tenant_stores(self):
        with Session(self.engine) as session:
            self.add_role(session, self.user_id, self.global_role_id)
            user = session.get(User, self.user_id)
            service = AuthorizationService()
            service.require_permission(session, user, "sell", self.store_a_id)
            service.require_permission(session, user, "sell", self.store_a2_id)
            with self.assertRaises(PermissionDeniedError):
                service.require_permission(session, user, "sell", self.store_b_id)
            with self.assertRaises(PermissionDeniedError):
                service.require_permission(
                    session, user, "sell", self.inactive_store_id
                )

    def test_all_tenant_scope_still_requires_active_employee(self):
        with Session(self.engine) as session:
            user = session.get(User, self.user_no_employee_id)
            self.add_role(session, user.id, self.global_role_id)
            with self.assertRaises(PermissionDeniedError):
                AuthorizationService().require_permission(
                    session, user, "sell", self.store_a_id
                )

    def test_tenant_safe_role_assignment_rejects_cross_tenant_role(self):
        with Session(self.engine) as session:
            with self.assertRaises(AuthorizationError):
                AuthorizationService().assign_role(
                    session,
                    self.tenant_a_id,
                    self.user_id,
                    self.cross_tenant_role_id,
                )

    def test_tenant_safe_role_assignment_accepts_matching_tenant(self):
        with Session(self.engine) as session:
            AuthorizationService().assign_role(
                session, self.tenant_a_id, self.user_id, self.assigned_role_id
            )
            assignment = session.get(
                UserRole,
                {"user_id": self.user_id, "role_id": self.assigned_role_id},
            )
            self.assertIsNotNone(assignment)

    def test_permission_grant_requires_role_from_current_tenant(self):
        with Session(self.engine) as session:
            with self.assertRaises(AuthorizationError):
                AuthorizationService().grant_permission(
                    session,
                    self.tenant_a_id,
                    self.cross_tenant_role_id,
                    "sell",
                    ALL_TENANT_STORES,
                )

    def test_authorization_seed_creates_scoped_roles_and_is_idempotent(self):
        with Session(self.engine) as session:
            seed_authorization(session, self.tenant_a_id)
            session.flush()
            seed_authorization(session, self.tenant_a_id)
            session.commit()
        with Session(self.engine) as session:
            sales = session.query(Role).filter_by(
                tenant_id=self.tenant_a_id, name="Sales"
            ).one()
            sales_global = session.query(Role).filter_by(
                tenant_id=self.tenant_a_id, name="Sales Global"
            ).one()
            sell_permission = session.query(Permission).filter_by(code="sell").one()
            self.assertEqual(
                session.get(
                    RolePermission,
                    {"role_id": sales.id, "permission_id": sell_permission.id},
                ).scope,
                ASSIGNED_STORES,
            )
            self.assertEqual(
                session.get(
                    RolePermission,
                    {
                        "role_id": sales_global.id,
                        "permission_id": sell_permission.id,
                    },
                ).scope,
                ALL_TENANT_STORES,
            )
            self.assertEqual(
                session.query(Role).filter_by(tenant_id=self.tenant_a_id).count(), 4
            )

    def test_require_permission_dependency_returns_403_when_denied(self):
        dependency = require_permission("sell")
        with Session(self.engine) as session:
            user = session.get(User, self.user_id)
            with self.assertRaises(HTTPException) as context:
                dependency(None, user, session)
        self.assertEqual(context.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()