from __future__ import annotations
"""
Eden Testing Infrastructure

Provides Async TestClient, fixtures, and utilities for modern Eden applications.
Supports database isolation via transactions and context-safe mocking.
"""


import asyncio
from contextlib import asynccontextmanager
import contextvars
from datetime import datetime, timedelta
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Union
from dataclasses import dataclass

import httpx
import jwt
import pytest

from starlette.types import ASGIApp

from eden.app import Eden, create_app
from eden.config import Config, set_config, get_config
from eden.db.session import Database, set_session, reset_session, get_session
from eden.db import Model
from eden.context import (
    set_current_user, 
    set_current_tenant_id, 
    set_request_id,
    set_app
)

@dataclass
class TestUser:
    """Mock user for testing."""
    __test__ = False
    id: int = 1
    email: str = "testuser@example.com"
    name: str = "Test User"
    password: str = "testpass123"
    is_active: bool = True
    is_staff: bool = False
    is_superuser: bool = False

    def to_dict(self) -> Dict[str, Any]:
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
    """Mock tenant for testing."""
    __test__ = False
    id: str = "test-tenant-1"
    name: str = "Test Tenant"
    slug: str = "test-tenant"

class EdenTestClient(httpx.AsyncClient):
    """
    Elite Async TestClient for Eden applications.
    Built on httpx for true async request handling.
    """
    
    def __init__(
        self, 
        app: ASGIApp, 
        base_url: str = "http://testserver", 
        **kwargs
    ):
        super().__init__(
            transport=httpx.ASGITransport(app=app), # type: ignore
            base_url=base_url,
            **kwargs
        )
        self.app = app
        self._current_user: Optional[TestUser] = None
        self._current_tenant: Optional[TestTenant] = None

    def set_user(self, user: Optional[TestUser]) -> None:
        """Authenticate subsequent requests as this user."""
        self._current_user = user
        if user:
            token = self._generate_token(user)
            self.headers["Authorization"] = f"Bearer {token}"
        else:
            self.headers.pop("Authorization", None)

    def set_tenant(self, tenant: Optional[Union[TestTenant, str]]) -> None:
        """Set tenant context for subsequent requests."""
        if isinstance(tenant, TestTenant):
            self._current_tenant = tenant
            tenant_id = tenant.id
        else:
            tenant_id = tenant
        
        if tenant_id:
            self.headers["X-Tenant-ID"] = tenant_id
        else:
            self.headers.pop("X-Tenant-ID", None)

    async def login(self, email: str = "testuser@example.com") -> TestUser:
        """Simulate a login by setting a test user."""
        user = TestUser(email=email, is_staff=email.startswith("admin"))
        self.set_user(user)
        return user

    def logout(self) -> None:
        """Clear authentication."""
        self.set_user(None)

    @asynccontextmanager
    async def context(self, user: Optional[Any] = None, tenant: Optional[Any] = None):
        """
        Asynchronous context manager for isolating request state.
        
        Example:
            async with client.context(user=mock_user):
                response = await client.get("/")
        """
        old_user = self._current_user
        old_tenant = self._current_tenant
        
        if user is not None:
            self.set_user(user)
        if tenant is not None:
            self.set_tenant(tenant)
            
        try:
            yield self
        finally:
            self.set_user(old_user)
            self.set_tenant(old_tenant)

    def _generate_token(self, user: TestUser) -> str:
        """Generate a test-signed JWT."""
        # Try to get secret from app first
        secret = getattr(self.app, "secret_key", None)
        if not secret:
            config = get_config()
            secret = getattr(config, "SECRET_KEY", "test-secret-key")
        
        from datetime import datetime, timezone, timedelta
        payload = {
            "sub": str(getattr(user, "id", "0")),
            "email": getattr(user, "email", "test@example.com"),
            "is_staff": getattr(user, "is_staff", False),
            "exp": datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1),
            "test": True,
        }
        return jwt.encode(payload, secret, algorithm="HS256")

# --- Pytest Fixtures ---

def eden_config_fixture():
    """Pytest fixture factory that ensures ConfigManager is reset between tests."""
    import pytest
    
    @pytest.fixture(autouse=True)
    def _reset_eden_config():
        from eden.config import ConfigManager
        yield
        ConfigManager.instance().reset()
    
    return _reset_eden_config

# Pytest-asyncio session-scoped event loop is configured in pyproject.toml

@pytest.fixture(scope="session")
async def test_app() -> AsyncGenerator[Eden, None]:
    """
    Create and configure the Eden application for testing.
    Ensures environment-specific (.env.test) overrides are applied.
    """
    import os
    from eden.config import ConfigManager, set_config
    
    # Force environment to test
    os.environ["EDEN_ENV"] = "test"
    
    # Reload configuration to pick up .env.test and OS env overrides
    ConfigManager.instance().reset()
    config = ConfigManager.instance().load()
    
    # Standardize test database: use in-memory SQLite by default
    # This prevents Windows PermissionError (file locking) and is much faster.
    if not config.database_url or config.database_url == "sqlite:///dist/db.sqlite3":
         config.database_url = "sqlite+aiosqlite:///:memory:"

    # Allow explicit DATABASE_URL overrides in test invocations (e.g. CI testing against Postgres)
    env_database_url = os.getenv("DATABASE_URL")
    if env_database_url:
        config.database_url = env_database_url

    # Apply standard test overrides if not already set by env
    if not config.secret_key:
        config.secret_key = "test-secret-key-for-eden-tests"
    config.debug = True
    
    set_config(config)
    
    # Proactively import models for metadata registration before table creation
    # This ensures all relationships are properly Bridge-ed.
    import contextlib
    with contextlib.suppress(ImportError):
        import eden.auth.models  # noqa: F401
    with contextlib.suppress(ImportError):
        import eden.tenancy.models  # noqa: F401
    with contextlib.suppress(ImportError):
        import eden.admin.models  # noqa: F401
    with contextlib.suppress(ImportError):
        import eden.payments.models  # noqa: F401

    app = create_app()
    # Initialize app state so db is available
    app.state.db = Database(config.get_database_url(), echo=True)
    await app.state.db.connect(create_tables=True)
    
    try:
        yield app
    finally:
        # Layer 1 stability: ensure database disconnect on teardown
        # This prevents lingering connections from causing issues on Windows.
        if hasattr(app.state, "db"):
            await app.state.db.disconnect()

@pytest.fixture(scope="session")
async def db(test_app: Eden) -> Database:
    """Provides access to the test database."""
    return test_app.state.db

@pytest.fixture
async def db_transaction(db: Database) -> AsyncGenerator[None, None]:
    """
    Forces a transaction per test and rolls it back at the end.
    This ensures complete database isolation between tests.
    """
    async with db.engine.connect() as connection:
        # Start a transaction on the connection
        transaction = await connection.begin()
        
        # Create a session bound to this connection
        from sqlalchemy.ext.asyncio import AsyncSession
        # Ensure the session uses the active connection and wraps its commits in SAVEPOINTs
        session = AsyncSession(
            bind=connection, 
            expire_on_commit=False, 
            join_transaction_mode="create_savepoint"
        )
        
        # Inject this session into the Eden context
        token = set_session(session)
        
        try:
            # We also start an initial transaction for the session so that 
            # any code calling session.commit() targets a savepoint.
            await session.begin()
            
            # tables already created in test_app fixture
            
            yield
        finally:
            # Revert everything at the connection level
            await transaction.rollback()
            await session.close()
            reset_session(token)

@pytest.fixture
async def client(test_app: Eden, db_transaction) -> AsyncGenerator[EdenTestClient, None]:
    """Provides an async test client configured for the test app."""
    async with EdenTestClient(test_app) as c:
        yield c

@pytest.fixture
def test_user() -> TestUser:
    """Provides a standard test user."""
    return TestUser()

@pytest.fixture
def admin_user() -> TestUser:
    """Provides an admin test user."""
    return TestUser(id=2, email="admin@example.com", is_staff=True, is_superuser=True)

# --- Utilities ---

@asynccontextmanager
async def mock_context(
    user: Optional[TestUser] = None,
    tenant_id: Optional[str] = None,
    app: Optional[Eden] = None
) -> AsyncGenerator[None, None]:
    """
    Mock the global Eden context for unit tests.
    """
    tokens = []
    if app:
        tokens.append(set_app(app))
    if user:
        tokens.append(set_current_user(user))
    if tenant_id:
        tokens.append(set_current_tenant_id(tenant_id))
    
    try:
        yield
    finally:
        # Contextvars are automatically reset in their context, 
        # but we can be explicit if needed.
        pass

def assert_status(response: httpx.Response, expected: int) -> None:
    """Better error message for status code assertions."""
    assert response.status_code == expected, f"Expected {expected}, got {response.status_code}. Body: {response.text}"

class UserFactory:
    """Async factory for creating real database users in tests."""
    
    def __init__(self, db: Database):
        self.db = db
        # Attempt to get the real User model if it exists
        try:
            from eden.auth.models import User
            self.user_model = User
        except ImportError:
            self.user_model = None

    async def create(self, **kwargs) -> Any:
        if not self.user_model:
            return TestUser(**kwargs)
            
        # Ensure default password if not provided
        password = kwargs.pop("password", "testpass123")
        
        # Ensure default email/identity
        if "email" not in kwargs:
            import uuid
            kwargs["email"] = f"user_{uuid.uuid4().hex[:8]}@example.com"
            
        user = self.user_model(**kwargs)
        # Use set_password to handle hashing and avoid init errors
        user.set_password(password)
        
        # Check if we're in a test transaction context
        from eden.db.session import get_session
        session = get_session()
        if session:
            # We're in a test transaction, add to session without committing
            session.add(user)
            await session.flush()
        else:
            # Normal operation, commit the save
            await user.save()
        return user

    async def create_admin(self, **kwargs) -> Any:
        kwargs.setdefault("is_staff", True)
        kwargs.setdefault("is_superuser", True)
        return await self.create(**kwargs)

    async def create_batch(self, count: int, **kwargs) -> List[Any]:
        users = []
        for i in range(count):
            batch_kwargs = kwargs.copy()
            if "email" in batch_kwargs:
                parts = batch_kwargs["email"].split("@")
                batch_kwargs["email"] = f"{parts[0]}_{i}@{parts[1]}"
            users.append(await self.create(**batch_kwargs))
        return users

class TenantFactory:
    """Async factory for creating real database tenants in tests."""
    
    def __init__(self, db: Database):
        self.db = db
        try:
            from eden.tenancy.models import Tenant
            self.tenant_model = Tenant
        except ImportError:
            self.tenant_model = None

    async def create(self, **kwargs) -> Any:
        if not self.tenant_model:
            return TestTenant(**kwargs)
            
        tenant = self.tenant_model(**kwargs)
        await tenant.save()
        return tenant

@pytest.fixture
async def user_factory(db_transaction) -> UserFactory:
    """Provides a user factory for tests."""
    return UserFactory(db_transaction)

@pytest.fixture
async def tenant_factory(db: Database) -> TenantFactory:
    """Provides a tenant factory for tests."""
    return TenantFactory(db)

@pytest.fixture
def mock_stripe():
    """Mocks stripe API for testing."""
    import unittest.mock
    mock = unittest.mock.MagicMock()
    mock.Charge.create.return_value = {"status": "succeeded", "id": "ch_123"}
    return mock

@pytest.fixture
def mock_email():
    """Mocks email sending for testing."""
    import unittest.mock
    return unittest.mock.AsyncMock()

@pytest.fixture
def mock_s3():
    """Mocks S3/Storage API for testing."""
    import unittest.mock
    mock = unittest.mock.MagicMock()
    mock.put_object.return_value = {"ETag": "test"}
    return mock

__all__ = [
    "EdenTestClient",
    "TestUser",
    "TestTenant",
    "test_app",
    "db",
    "db_transaction",
    "client",
    "test_user",
    "admin_user",
    "user_factory",
    "tenant_factory",
    "mock_stripe",
    "mock_email",
    "mock_s3",
    "mock_context",
    "assert_status",
    "UserFactory",
    "TenantFactory",
    "eden_config_fixture",
]
