import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_auth_db
from app.database.base import Base
from app.database.session import get_db
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.tenant import Tenant
from app.models.user import User
from app.models.user_role import UserRole
from app.security.jwt import create_access_token
from main import app


TEST_SECRET = "role-management-test-secret-never-used-outside-123456"


class RoleManagementApiTests(unittest.TestCase):
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
            all_permission = Permission(code="ALL")
            users_permission = Permission(code="users.manage")
            roles_permission = Permission(code="roles.manage")
            permissions_permission = Permission(code="permissions.manage")
            sell_permission = Permission(code="sell")
            session.add_all(
                [
                    all_permission,
                    users_permission,
                    roles_permission,
                    permissions_permission,
                    sell_permission,
                ]
            )
            session.flush()

            admin_role = Role(tenant_id=tenant.id, name="Admin")
            manager_role = Role(tenant_id=tenant.id, name="Role Manager")
            other_role = Role(tenant_id=other_tenant.id, name="Other Tenant Role")
            session.add_all([admin_role, manager_role, other_role])
            session.flush()

            admin = User(
                tenant_id=tenant.id,
                username="admin",
                password_hash="test-only-hash",
                email="admin@example.com",
                mobile="+15550000001",
                is_active=True,
            )
            manager = User(
                tenant_id=tenant.id,
                username="manager",
                password_hash="test-only-hash",
                email="manager@example.com",
                mobile="+15550000002",
                is_active=True,
            )
            target = User(
                tenant_id=tenant.id,
                username="target",
                password_hash="test-only-hash",
                email="target@example.com",
                mobile="+15550000003",
                is_active=True,
            )
            other_tenant_user = User(
                tenant_id=other_tenant.id,
                username="other",
                password_hash="test-only-hash",
                email="other@example.com",
                mobile="+15550000004",
                is_active=True,
            )
            session.add_all([admin, manager, target, other_tenant_user])
            session.flush()

            session.add_all(
                [
                    UserRole(user_id=admin.id, role_id=admin_role.id),
                    RolePermission(
                        role_id=admin_role.id,
                        permission_id=all_permission.id,
                        scope="assigned_stores",
                    ),
                    UserRole(user_id=manager.id, role_id=manager_role.id),
                    RolePermission(
                        role_id=manager_role.id,
                        permission_id=users_permission.id,
                        scope="assigned_stores",
                    ),
                    RolePermission(
                        role_id=manager_role.id,
                        permission_id=roles_permission.id,
                        scope="assigned_stores",
                    ),
                    RolePermission(
                        role_id=manager_role.id,
                        permission_id=permissions_permission.id,
                        scope="assigned_stores",
                    ),
                ]
            )
            session.commit()
            self.tenant_id = tenant.id
            self.admin_role_id = admin_role.id
            self.manager_role_id = manager_role.id
            self.target_user_id = target.id
            self.other_tenant_role_id = other_role.id
            self.other_tenant_user_id = other_tenant_user.id
            self.admin_token = create_access_token(admin.id)
            self.manager_token = create_access_token(manager.id)

        def override_db():
            with Session(self.engine) as session:
                yield session

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_auth_db] = override_db

    def tearDown(self):
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_auth_db, None)
        self.environment.stop()

    def client(self, token=None):
        token = token or self.admin_token
        return TestClient(app, headers={"Authorization": f"Bearer {token}"})

    def test_role_list_is_tenant_scoped(self):
        response = self.client().get("/api/roles")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([role["name"] for role in response.json()], ["Admin", "Role Manager"])

    def test_permission_catalog_hides_reserved_all_permission(self):
        response = self.client().get("/api/roles/form-data")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["can_manage_permissions"])
        self.assertNotIn("ALL", [permission["code"] for permission in response.json()["permissions"]])

    def test_create_role_and_reject_duplicate_name(self):
        payload = {"name": "Sales Supervisor", "description": "Supervises sales"}
        created = self.client().post("/api/roles", json=payload)
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(created.json()["name"], "Sales Supervisor")
        duplicate = self.client().post("/api/roles", json=payload)
        self.assertEqual(duplicate.status_code, 409)

    def test_replace_permissions_on_custom_role(self):
        created = self.client().post("/api/roles", json={"name": "Sales"})
        role_id = created.json()["id"]
        response = self.client().put(
            f"/api/roles/{role_id}/permissions",
            json={
                "permissions": [
                    {"permission_code": "sell", "scope": "all_tenant_stores"}
                ]
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["permissions"][0]["permission_code"], "sell")
        self.assertEqual(response.json()["permissions"][0]["scope"], "all_tenant_stores")

    def test_reserved_all_permission_cannot_be_granted_to_custom_role(self):
        created = self.client().post("/api/roles", json={"name": "Custom"})
        response = self.client().put(
            f"/api/roles/{created.json()['id']}/permissions",
            json={"permissions": [{"permission_code": "ALL", "scope": "assigned_stores"}]},
        )
        self.assertEqual(response.status_code, 409)

    def test_system_administrator_role_permissions_are_protected(self):
        response = self.client().put(
            f"/api/roles/{self.admin_role_id}/permissions",
            json={"permissions": []},
        )
        self.assertEqual(response.status_code, 409)

    def test_role_manager_without_all_cannot_change_permissions(self):
        created = self.client(token=self.manager_token).post(
            "/api/roles",
            json={"name": "Created by manager"},
        )
        self.assertEqual(created.status_code, 201, created.text)
        response = self.client(token=self.manager_token).put(
            f"/api/roles/{created.json()['id']}/permissions",
            json={"permissions": [{"permission_code": "sell", "scope": "assigned_stores"}]},
        )
        self.assertEqual(response.status_code, 403)

    def test_role_manager_cannot_assign_system_administrator_role(self):
        response = self.client(token=self.manager_token).post(
            f"/api/users/{self.target_user_id}/roles/{self.admin_role_id}",
        )
        self.assertEqual(response.status_code, 403)

    def test_role_cannot_be_updated_across_tenants(self):
        response = self.client().patch(
            f"/api/roles/{self.other_tenant_role_id}",
            json={"name": "Stolen role name"},
        )
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
