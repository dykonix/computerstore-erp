import os
import unittest
from datetime import timedelta
from unittest.mock import patch

import jwt
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import (
    get_current_employee,
    get_current_tenant,
    get_current_tenant_id,
    get_current_user,
)
from app.api.routes.auth import login
from app.database.base import Base
from app.models.employee import Employee
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import LoginRequest
from app.security.jwt import create_access_token
from app.security.password import hash_password
from app.services.auth_service import AuthService
from main import app


TEST_SECRET = "test-only-secret-that-is-not-used-outside-tests-987654321"
TEST_PASSWORD = "test-password-only"


class AuthenticationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(cls.engine)
        cls.encoded_password = hash_password(TEST_PASSWORD)

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
        self.user_sequence = 0
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
            session.add_all([employee_a, employee_b, inactive_employee])
            session.flush()
            self.tenant_a_id = tenant_a.id
            self.tenant_b_id = tenant_b.id
            self.employee_a_id = employee_a.id
            self.employee_b_id = employee_b.id
            self.inactive_employee_id = inactive_employee.id
            session.commit()

    def tearDown(self):
        self.environment.stop()

    def add_user(
        self,
        *,
        tenant_id=None,
        employee_id=None,
        email="sales@example.com",
        active=True,
        password_hash=None,
    ):
        self.user_sequence += 1
        with Session(self.engine) as session:
            user = User(
                tenant_id=tenant_id or self.tenant_a_id,
                username="test-user",
                password_hash=password_hash or self.encoded_password,
                email=email,
                mobile=f"+1555{self.user_sequence:07d}",
                employee_id=employee_id,
                is_active=active,
            )
            session.add(user)
            session.commit()
            return user.id

    def login_request(self, **overrides):
        values = {"email": "  Sales@Example.com ", "password": TEST_PASSWORD}
        values.update(overrides)
        return LoginRequest(**values)

    def test_valid_login_returns_minimal_access_token_response(self):
        self.add_user(employee_id=self.employee_a_id)
        with Session(self.engine) as session:
            response = login(self.login_request(), session, AuthService())
        self.assertEqual(response.token_type, "bearer")
        self.assertEqual(set(response.model_dump()), {"access_token", "token_type"})
        payload = jwt.decode(
            response.access_token,
            TEST_SECRET,
            algorithms=["HS256"],
            options={"require": ["sub", "exp"]},
        )
        self.assertEqual(set(payload), {"sub", "exp"})

    def test_auth_login_route_is_registered(self):
        self.assertIn("/auth/login", app.openapi()["paths"])

    def test_email_is_normalized_before_lookup(self):
        self.add_user(employee_id=self.employee_a_id)
        with Session(self.engine) as session:
            response = login(
                LoginRequest(email="  SALES@EXAMPLE.COM  ", password=TEST_PASSWORD),
                session,
                AuthService(),
            )
        self.assertTrue(response.access_token)

    def test_wrong_password_and_unknown_email_use_same_response(self):
        self.add_user(employee_id=self.employee_a_id)
        results = []
        for request in (
            self.login_request(password="wrong-password"),
            self.login_request(email="unknown@example.com"),
        ):
            with Session(self.engine) as session:
                with self.assertRaises(HTTPException) as context:
                    login(request, session, AuthService())
            results.append((context.exception.status_code, context.exception.detail))
        self.assertEqual(results, [(401, "Invalid email or password")] * 2)

    def test_inactive_user_is_rejected_with_generic_credentials_error(self):
        self.add_user(employee_id=self.employee_a_id, active=False)
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as context:
                login(self.login_request(), session, AuthService())
        self.assertEqual(context.exception.status_code, 401)
        self.assertEqual(context.exception.detail, "Invalid email or password")

    def test_login_rejects_user_without_employee(self):
        self.add_user(employee_id=None)
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as context:
                login(self.login_request(), session, AuthService())
        self.assertEqual(context.exception.status_code, 401)
        self.assertEqual(context.exception.detail, "Invalid email or password")

    def test_login_rejects_cross_tenant_employee(self):
        self.add_user(employee_id=self.employee_b_id)
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as context:
                login(self.login_request(), session, AuthService())
        self.assertEqual(context.exception.status_code, 401)
        self.assertEqual(context.exception.detail, "Invalid email or password")

    def test_login_rejects_inactive_employee(self):
        self.add_user(employee_id=self.inactive_employee_id)
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as context:
                login(self.login_request(), session, AuthService())
        self.assertEqual(context.exception.status_code, 401)
        self.assertEqual(context.exception.detail, "Invalid email or password")

    def test_current_user_resolves_user_id_from_valid_token(self):
        expected_user_id = self.add_user(employee_id=self.employee_a_id)
        token = create_access_token(expected_user_id)
        with Session(self.engine) as session:
            user = get_current_user(
                HTTPAuthorizationCredentials(scheme="Bearer", credentials=token),
                session,
            )
        self.assertEqual(user.id, expected_user_id)

    def test_current_user_rejects_invalid_token(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as context:
                get_current_user(
                    HTTPAuthorizationCredentials(
                        scheme="Bearer", credentials="not-a-jwt"
                    ),
                    session,
                )
        self.assertEqual(context.exception.status_code, 401)

    def test_current_user_rejects_expired_token(self):
        user_id = self.add_user(employee_id=self.employee_a_id)
        token = create_access_token(user_id, timedelta(seconds=-1))
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as context:
                get_current_user(
                    HTTPAuthorizationCredentials(scheme="Bearer", credentials=token),
                    session,
                )
        self.assertEqual(context.exception.status_code, 401)

    def test_current_user_rejects_missing_bearer_token(self):
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as context:
                get_current_user(None, session)
        self.assertEqual(context.exception.status_code, 401)

    def test_current_user_rejects_inactive_user(self):
        user_id = self.add_user(employee_id=self.employee_a_id, active=False)
        token = create_access_token(user_id)
        with Session(self.engine) as session:
            with self.assertRaises(HTTPException) as context:
                get_current_user(
                    HTTPAuthorizationCredentials(scheme="Bearer", credentials=token),
                    session,
                )
        self.assertEqual(context.exception.status_code, 401)

    def test_tenant_is_derived_from_authenticated_user(self):
        user_id = self.add_user(
            tenant_id=self.tenant_b_id,
            employee_id=self.employee_b_id,
            email="tenant-b@example.com",
        )
        token = create_access_token(user_id)
        with Session(self.engine) as session:
            user = get_current_user(
                HTTPAuthorizationCredentials(scheme="Bearer", credentials=token),
                session,
            )
            tenant_id = get_current_tenant(user)
        self.assertEqual(tenant_id, self.tenant_b_id)

    def test_current_employee_is_resolved_from_user_and_tenant(self):
        user_id = self.add_user(employee_id=self.employee_a_id)
        token = create_access_token(user_id)
        with Session(self.engine) as session:
            user = get_current_user(
                HTTPAuthorizationCredentials(scheme="Bearer", credentials=token),
                session,
            )
            employee = get_current_employee(user, session)
        self.assertEqual(employee.id, self.employee_a_id)
        self.assertEqual(employee.tenant_id, self.tenant_a_id)

    def test_current_employee_rejects_missing_cross_tenant_or_inactive_employee(self):
        invalid_cases = (
            (self.tenant_a_id, None, "missing@example.com", True),
            (self.tenant_a_id, self.employee_b_id, "cross@example.com", True),
            (self.tenant_a_id, self.inactive_employee_id, "inactive@example.com", True),
        )
        for tenant_id, employee_id, email, active in invalid_cases:
            user_id = self.add_user(
                tenant_id=tenant_id,
                employee_id=employee_id,
                email=email,
                active=active,
            )
            with Session(self.engine) as session:
                user = session.get(User, user_id)
                with self.assertRaises(HTTPException) as context:
                    get_current_employee(user, session)
            self.assertEqual(context.exception.status_code, 403)

    def test_login_request_rejects_client_tenant_or_employee_ids(self):
        with self.assertRaises(ValidationError):
            LoginRequest(
                email="sales@example.com",
                password=TEST_PASSWORD,
                tenant_id=self.tenant_b_id,
            )
        with self.assertRaises(ValidationError):
            LoginRequest(
                email="sales@example.com",
                password=TEST_PASSWORD,
                employee_id=self.employee_b_id,
            )


if __name__ == "__main__":
    unittest.main()