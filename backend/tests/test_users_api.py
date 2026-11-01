import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_auth_db
from app.database.base import Base
from app.database.session import get_db
from app.models.employee import Employee
from app.models.employee_store import EmployeeStore
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.tenant import Tenant
from app.models.store import Store
from app.models.user import User
from app.models.user_role import UserRole
from app.security.jwt import create_access_token
from main import app


TEST_SECRET = "iam-test-secret-never-used-outside-tests-1234567890"


class UserManagementApiTests(unittest.TestCase):
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
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_auth_db, None)
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
            tenant = Tenant(name="Tenant A")
            other_tenant = Tenant(name="Tenant B")
            session.add_all([tenant, other_tenant])
            session.flush()
            employee = Employee(
                tenant_id=tenant.id,
                email="admin@example.com",
                name="Admin Employee",
            )
            other_employee = Employee(
                tenant_id=other_tenant.id,
                email="other@example.com",
                name="Other Employee",
            )
            permission = Permission(code="users.manage")
            roles_permission = Permission(code="roles.manage")
            role = Role(tenant_id=tenant.id, name="Admin")
            session.add_all([employee, other_employee, permission, roles_permission, role])
            session.flush()
            admin = User(
                tenant_id=tenant.id,
                username="admin",
                password_hash="test-only-hash",
                email="admin@example.com",
                mobile="+15550000001",
                employee_id=employee.id,
                is_active=True,
            )
            other_user = User(
                tenant_id=other_tenant.id,
                username="other",
                password_hash="test-only-hash",
                email="other-user@example.com",
                mobile="+15550000002",
                employee_id=other_employee.id,
                is_active=True,
            )
            session.add_all([admin, other_user])
            session.flush()
            session.add_all(
                [
                    UserRole(user_id=admin.id, role_id=role.id),
                    RolePermission(
                        role_id=role.id,
                        permission_id=permission.id,
                        scope="all_tenant_stores",
                    ),
                    RolePermission(
                        role_id=role.id,
                        permission_id=roles_permission.id,
                        scope="all_tenant_stores",
                    ),
                ]
            )
            session.commit()
            self.tenant_id = tenant.id
            self.admin_id = admin.id
            self.employee_id = employee.id
            self.other_user_id = other_user.id
            self.token = create_access_token(admin.id)

        def override_db():
            with Session(self.engine) as session:
                yield session

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_auth_db] = override_db

    def tearDown(self):
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_auth_db, None)
        self.environment.stop()

    def client(self):
        return TestClient(app, headers={"Authorization": f"Bearer {self.token}"})

    def test_user_list_is_tenant_scoped_and_never_returns_password_hash(self):
        response = self.client().get("/api/users")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["email"] for item in response.json()], ["admin@example.com"])
        self.assertNotIn("password_hash", response.json()[0])

    def test_create_user_hashes_initial_password_and_returns_safe_response(self):
        response = self.client().post(
            "/api/users",
            json={
                "username": "new-user",
                "email": "New.User@Example.com",
                "mobile": "+1 (555) 000-0003",
                "employee_id": None,
                "initial_password": "A-strong-initial-password",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        payload = response.json()
        self.assertEqual(payload["email"], "new.user@example.com")
        self.assertNotIn("initial_password", payload)
        self.assertNotIn("password_hash", payload)
        with Session(self.engine) as session:
            created = session.get(User, payload["id"])
            self.assertNotEqual(created.password_hash, "A-strong-initial-password")
            self.assertTrue(created.password_hash)

    def test_create_user_assigns_roles_and_selected_stores_atomically(self):
        with Session(self.engine) as session:
            employee = Employee(
                tenant_id=self.tenant_id,
                email="sales@example.com",
                name="Sales Employee",
            )
            role = Role(tenant_id=self.tenant_id, name="Sales")
            permission = session.scalar(
                select(Permission).where(Permission.code == "sell")
            )
            if permission is None:
                permission = Permission(code="sell", description="Create sales")
                session.add(permission)
            store = Store(tenant_id=self.tenant_id, name="Store A")
            session.add_all([employee, role, store])
            session.flush()
            session.add(
                RolePermission(
                    role_id=role.id,
                    permission_id=permission.id,
                    scope="assigned_stores",
                )
            )
            session.commit()
            employee_id, role_id, store_id = employee.id, role.id, store.id

        response = self.client().post(
            "/api/users",
            json={
                "username": "sales-user",
                "email": "sales-user@example.com",
                "mobile": "+15550000003",
                "employee_id": employee_id,
                "role_ids": [role_id],
                "store_ids": [store_id],
                "initial_password": "A-strong-initial-password",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        payload = response.json()
        self.assertEqual(payload["role_ids"], [role_id])
        self.assertEqual(payload["role_names"], ["Sales"])
        with Session(self.engine) as session:
            self.assertIsNotNone(
                session.get(UserRole, {"user_id": payload["id"], "role_id": role_id})
            )
            self.assertIsNotNone(
                session.get(
                    EmployeeStore,
                    {"employee_id": employee_id, "store_id": store_id},
                )
            )

    def test_create_user_rejects_store_access_without_linked_employee(self):
        response = self.client().post(
            "/api/users",
            json={
                "username": "store-user",
                "email": "store-user@example.com",
                "mobile": "+15550000004",
                "employee_id": None,
                "store_ids": [1],
                "initial_password": "A-strong-initial-password",
            },
        )
        self.assertEqual(response.status_code, 409)

    def test_user_list_requires_authentication(self):
        response = TestClient(app).get("/api/users")
        self.assertEqual(response.status_code, 401)

    def test_role_assignment_cannot_target_another_tenant(self):
        response = self.client().post(
            f"/api/users/{self.other_user_id}/roles/1",
        )
        self.assertEqual(response.status_code, 404)

    def test_admin_cannot_change_own_role_assignments(self):
        response = self.client().post(
            f"/api/users/{self.admin_id}/roles/1",
        )
        self.assertEqual(response.status_code, 400)

    def test_admin_cannot_deactivate_own_account(self):
        response = self.client().patch(
            f"/api/users/{self.admin_id}/status",
            json={"is_active": False},
        )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
