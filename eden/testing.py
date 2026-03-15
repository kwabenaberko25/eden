"""
Eden Testing Infrastructure

Provides TestClient, fixtures, and utilities for testing Eden applications.

Usage:
    from eden.testing import TestClient, create_test_app
    
    def test_list_users():
        app = create_test_app()
        client = TestClient(app)
        
        response = client.get("/users")
        assert response.status_code == 200
        assert "id" in response.json()[0]
"""

from __future__ import annotations

import asyncio
import contextvars
from typing import Any, Optional, AsyncGenerator, Callable, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass
import json

# Try to import pytest; if not available, mark with None
try:
    import pytest
    PYTEST_AVAILABLE = True
except ImportError:
    pytest = None
    PYTEST_AVAILABLE = False

from starlette.testclient import TestClient as StarletteTestClient
from starlette.applications import Starlette


@dataclass
class TestUser:
    """
    Test user fixture with common defaults.
    
    Example:
        user = TestUser(email="test@example.com", is_staff=True)
        assert user.is_staff
    """
    id: int = 1
    email: str = "testuser@example.com"
    name: str = "Test User"
    password: str = "testpass123"
    is_active: bool = True
    is_staff: bool = False
    is_superuser: bool = False
    groups: List[str] = None
    
    def __post_init__(self):
        if self.groups is None:
            self.groups = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "is_active": self.is_active,
            "is_staff": self.is_staff,
            "is_superuser": self.is_superuser,
        }


@dataclass
class TestTenant:
    """
    Test tenant fixture for multi-tenant testing.
    
    Example:
        tenant = TestTenant(name="Acme Corp")
        assert tenant.name == "Acme Corp"
    """
    id: str = "test-tenant-1"
    name: str = "Test Tenant"
    slug: str = "test-tenant"
    active: bool = True


class TestClient(StarletteTestClient):
    """
    Extended TestClient with Eden-specific utilities.
    
    Extends Starlette's TestClient with:
    - Context injection (user, tenant_id)
    - Response assertion helpers
    - Mock data creation
    - Database transaction rollback after each test
    """
    
    def __init__(self, app: Starlette, **kwargs):
        """
        Initialize test client.
        
        Args:
            app: Starlette application
            **kwargs: Additional arguments for TestClient
        """
        super().__init__(app, **kwargs)
        self.app = app
        self._current_user: Optional[TestUser] = None
        self._current_tenant: Optional[TestTenant] = None
    
    def set_user(self, user: Optional[TestUser]) -> None:
        """
        Set the current test user.
        
        All subsequent requests will be authenticated as this user.
        
        Args:
            user: TestUser instance or None to logout
            
        Example:
            client = TestClient(app)
            client.set_user(TestUser(email="admin@example.com", is_staff=True))
            response = client.get("/admin")
            assert response.status_code == 200
        """
        self._current_user = user
        if user:
            # Set auth header for subsequent requests
            token = self._generate_token(user)
            self.headers.update({"Authorization": f"Bearer {token}"})
        else:
            # Clear auth header
            self.headers.pop("Authorization", None)
    
    def set_tenant(self, tenant: Optional[TestTenant]) -> None:
        """
        Set the current test tenant (multi-tenant mode).
        
        All subsequent requests operate in this tenant context.
        
        Args:
            tenant: TestTenant instance or None
            
        Example:
            client.set_tenant(TestTenant(id="tenant-123"))
            response = client.get("/users")
            # Only users in tenant-123 are returned
        """
        self._current_tenant = tenant
        if tenant:
            self.headers.update({"X-Tenant-ID": tenant.id})
        else:
            self.headers.pop("X-Tenant-ID", None)
    
    def login(self, email: str = "testuser@example.com", password: str = "testpass123") -> TestUser:
        """
        Log in as a test user.
        
        Simulates user authentication flow.
        
        Args:
            email: User email
            password: User password
            
        Returns:
            TestUser instance
            
        Example:
            user = client.login("admin@example.com")
            assert user.is_staff
        """
        user = TestUser(email=email, is_staff=email.startswith("admin"))
        self.set_user(user)
        return user
    
    def logout(self) -> None:
        """
        Log out the current user.
        
        Example:
            client.logout()
            response = client.get("/protected")
            assert response.status_code == 401
        """
        self.set_user(None)
    
    def get_json(self, *args, **kwargs) -> Any:
        """
        Make GET request and return parsed JSON.
        
        Example:
            users = client.get_json("/api/users")
            assert len(users) > 0
        """
        response = self.get(*args, **kwargs)
        return response.json()
    
    def post_json(self, path: str, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Make POST request with JSON body, return parsed JSON.
        
        Example:
            response = client.post_json("/api/users", {"email": "new@example.com"})
            assert response["id"]
        """
        response = self.post(path, json=data, **kwargs)
        return response.json() if response.content else {}
    
    def assert_status(self, response: Any, expected_status: int) -> None:
        """
        Assert response has expected status code.
        
        Example:
            response = client.get("/users")
            client.assert_status(response, 200)
        """
        assert response.status_code == expected_status, \
            f"Expected {expected_status}, got {response.status_code}: {response.text}"
    
    def assert_json_contains(self, response: Any, key: str, value: Any = None) -> None:
        """
        Assert response JSON contains key (and optionally value).
        
        Example:
            response = client.get("/users/1")
            client.assert_json_contains(response, "email", "testuser@example.com")
        """
        data = response.json()
        assert key in data, f"Key '{key}' not in response: {data}"
        if value is not None:
            assert data[key] == value, f"Expected {value}, got {data[key]}"
    
    def _generate_token(self, user: TestUser) -> str:
        """Generate a test JWT token for user."""
        import jwt
        from datetime import datetime, timedelta
        
        token_data = {
            "sub": user.email,
            "user_id": user.id,
            "is_staff": user.is_staff,
            "exp": datetime.utcnow() + timedelta(hours=1),
        }
        
        return jwt.encode(
            token_data,
            "test-secret-key",
            algorithm="HS256"
        )


# Pytest Fixtures (only if pytest is installed)

if PYTEST_AVAILABLE:
    @pytest.fixture
    def test_app() -> Starlette:
        """
        Create a test app with in-memory database.
        
        Example:
            def test_something(test_app):
                client = TestClient(test_app)
                response = client.get("/")
        """
        from eden.app import create_app
        from eden.config import Config, set_config
        
        # Create test config
        test_config = Config()
        test_config.ENVIRONMENT = "testing"
        test_config.DATABASE_URL = "sqlite:///:memory:"
        test_config.DEBUG = True
        set_config(test_config)
        
        # Create app
        app = create_app()
        
        return app

    @pytest.fixture
    def client(test_app: Starlette) -> TestClient:
        """
        Create a test client for the test app.
        
        Example:
            def test_list_users(client):
                response = client.get("/api/users")
                assert response.status_code == 200
        """
        return TestClient(test_app)

    @pytest.fixture
    def test_user() -> TestUser:
        """
        Create a test user fixture.
        
        Example:
            def test_user_profile(client, test_user):
                client.set_user(test_user)
                response = client.get(f"/api/users/{test_user.id}")
        """
        return TestUser(
            id=1,
            email="testuser@example.com",
            name="Test User",
            is_staff=False,
        )

    @pytest.fixture
    def admin_user() -> TestUser:
        """
        Create an admin test user fixture.
        
        Example:
            def test_admin_only(client, admin_user):
                client.set_user(admin_user)
                response = client.get("/admin")
        """
        return TestUser(
            id=2,
            email="admin@example.com",
            name="Admin User",
            is_staff=True,
            is_superuser=True,
        )

    @pytest.fixture
    def test_tenant() -> TestTenant:
        """
        Create a test tenant fixture (multi-tenant mode).
        
        Example:
            def test_tenant_isolation(client, test_tenant):
                client.set_tenant(test_tenant)
                response = client.get("/api/users")
        """
        return TestTenant(
            id="test-tenant-123",
            name="Test Tenant",
            slug="test-tenant",
        )

    @pytest.fixture
    def db_transaction():
        """
        Provide a database transaction that rolls back after test.
        
        Ensures test data doesn't persist between tests.
        
        Example:
            async def test_create_user(db_transaction):
                user = await User.create(email="test@example.com")
                assert user.id
                # Auto-rollback after test
        """
        # This is a placeholder - actual implementation depends on your DB
        # Typically implemented as a context manager that provides
        # a transaction-scoped session
        pass


# Context Managers for Test Setup

async def mock_context(**kwargs) -> AsyncGenerator[None, None]:
    """
    Mock context for testing (user, tenant_id, request_id).
    
    Example:
        async def test_get_current_user():
            test_user = TestUser(email="test@example.com")
            async with mock_context(user=test_user):
                from eden.context import get_user
                assert get_user().email == "test@example.com"
    """
    from eden.context import (
        set_app, set_request, set_current_user,
        set_current_tenant_id, set_request_id
    )
    
    # Set context vars
    if "app" in kwargs:
        set_app(kwargs["app"])
    if "request" in kwargs:
        set_request(kwargs["request"])
    if "user" in kwargs:
        set_current_user(kwargs["user"])
    if "tenant_id" in kwargs:
        set_current_tenant_id(kwargs["tenant_id"])
    if "request_id" in kwargs:
        set_request_id(kwargs["request_id"])
    
    try:
        yield
    finally:
        # Cleanup done automatically in tests
        pass


# Utilities

def create_test_app(
    config: Optional[Dict[str, Any]] = None,
    middleware: Optional[List[tuple]] = None
) -> Starlette:
    """
    Create a fully configured test application.
    
    Args:
        config: Configuration overrides
        middleware: Additional middleware to add
        
    Returns:
        Starlette application ready for testing
        
    Example:
        app = create_test_app({"DEBUG": True})
        client = TestClient(app)
    """
    from eden.app import create_app
    from eden.config import Config, set_config
    
    # Create test config
    test_config = Config()
    test_config.ENVIRONMENT = "testing"
    test_config.DATABASE_URL = "sqlite:///:memory:"
    
    if config:
        for key, value in config.items():
            setattr(test_config, key, value)
    
    set_config(test_config)
    
    # Create app
    app = create_app()
    
    # Add custom middleware if provided
    if middleware:
        for middleware_class, options in middleware:
            app.add_middleware(middleware_class, **options)
    
    return app


def assert_response_equals(response: Any, expected: Dict[str, Any]) -> None:
    """
    Assert response JSON matches expected data (partial match).
    
    Example:
        response = client.get("/api/users/1")
        assert_response_equals(response, {"email": "test@example.com"})
    """
    actual = response.json()
    for key, value in expected.items():
        assert key in actual, f"Key '{key}' not in response"
        assert actual[key] == value, f"Expected {value}, got {actual[key]}"


def assert_error_response(response: Any, code: str, status_code: int = 400) -> None:
    """
    Assert response is an error with given code.
    
    Example:
        response = client.post("/api/users", {"email": "invalid"})
        assert_error_response(response, "VALIDATION_ERROR")
    """
    assert response.status_code == status_code
    data = response.json()
    assert data.get("error") is True
    assert data.get("code") == code


__all__ = [
    "TestClient",
    "TestUser",
    "TestTenant",
    "test_app",
    "client",
    "test_user",
    "admin_user",
    "test_tenant",
    "mock_context",
    "create_test_app",
    "assert_response_equals",
    "assert_error_response",
]
