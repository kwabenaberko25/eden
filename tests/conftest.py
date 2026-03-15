"""
Eden — Test configuration and shared fixtures.

Provides:
- TestClient: Enhanced async test client with context support
- Fixtures: Common test objects (app, db, user, admin, etc.)
- Utilities: Helper functions for testing

**Usage:**

    # Use fixture in test
    async def test_homepage(client: TestClient):
        response = await client.get("/")
        assert response.status_code == 200
    
    # Create authenticated user
    async def test_login(user_factory):
        user = await user_factory.create(email="test@example.com")
        assert user.id is not None
    
    # Access request context in tests
    async def test_with_context(client: TestClient):
        async with client.context(user=user):
            response = await client.get("/profile")
            assert response.status_code == 200
"""

from __future__ import annotations

import asyncio
import datetime
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, AsyncGenerator, Optional
from unittest.mock import MagicMock, AsyncMock, patch

from eden import Eden, Depends, Router, Request, Database
from eden.context import (
    context_manager,
    get_user,
    set_user,
    get_tenant_id,
    set_tenant,
)

if TYPE_CHECKING:
    from httpx import ASGITransport, AsyncClient, Response
    from eden.db import Model

# Try to import httpx - optional for standalone use
try:
    from httpx import ASGITransport, AsyncClient, Response
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False
    # Define placeholders if not available
    ASGITransport = None
    AsyncClient = None
    Response = None

# Try to import pytest - optional for standalone use
try:
    import pytest
    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False

# Try to import auth components - optional
try:
    from eden.auth import User as BaseUser
    from eden.auth.backends import PasswordHasher
    HAS_AUTH = True
except ImportError:
    HAS_AUTH = False


# ============================================================================
# TestClient — Enhanced async HTTP client with context support
# ============================================================================


class TestClient:
    """
    Enhanced async test client for Eden applications.
    
    Wraps httpx.AsyncClient with support for:
    - Context variables (user, tenant, etc.)
    - Request/response introspection
    - Multi-request session management
    
    **Usage:**
    
        # Basic request
        response = await client.get("/api/users")
        assert response.status_code == 200
        
        # With context
        async with client.context(user=user):
            response = await client.get("/profile")
            assert response.text == user.email
        
        # Set headers
        response = await client.get(
            "/api/protected",
            headers={"Authorization": f"Bearer {token}"}
        )
    
    Note: Requires httpx package (pip install httpx)
    """
    
    def __init__(self, app: Eden, base_url: str = "http://testserver"):
        """
        Initialize test client.
        
        Args:
            app: Eden application instance
            base_url: Base URL for requests
        
        Raises:
            ImportError: If httpx is not installed
        """
        if not HAS_HTTPX:
            raise ImportError(
                "TestClient requires httpx. Install with: pip install httpx"
            )
        
        self.app = app
        self.base_url = base_url
        self._client: Optional[AsyncClient] = None
        self._context_manager = context_manager
    
    async def __aenter__(self):
        """Async context manager entry."""
        transport = ASGITransport(app=self.app)
        self._client = AsyncClient(transport=transport, base_url=self.base_url)
        await self._client.__aenter__()
        return self
    
    async def __aexit__(self, *args):
        """Async context manager exit."""
        if self._client:
            await self._client.__aexit__(*args)
    
    @property
    def client(self) -> AsyncClient:
        """Get underlying httpx client."""
        if self._client is None:
            raise RuntimeError(
                "TestClient must be used as async context manager. "
                "Use: async with TestClient(app) as client: ..."
            )
        return self._client
    
    async def get(
        self,
        url: str,
        **kwargs
    ) -> Response:
        """GET request."""
        return await self.client.get(url, **kwargs)
    
    async def post(
        self,
        url: str,
        **kwargs
    ) -> Response:
        """POST request."""
        return await self.client.post(url, **kwargs)
    
    async def put(
        self,
        url: str,
        **kwargs
    ) -> Response:
        """PUT request."""
        return await self.client.put(url, **kwargs)
    
    async def patch(
        self,
        url: str,
        **kwargs
    ) -> Response:
        """PATCH request."""
        return await self.client.patch(url, **kwargs)
    
    async def delete(
        self,
        url: str,
        **kwargs
    ) -> Response:
        """DELETE request."""
        return await self.client.delete(url, **kwargs)
    
    async def head(
        self,
        url: str,
        **kwargs
    ) -> Response:
        """HEAD request."""
        return await self.client.head(url, **kwargs)
    
    async def options(
        self,
        url: str,
        **kwargs
    ) -> Response:
        """OPTIONS request."""
        return await self.client.options(url, **kwargs)
    
    @asynccontextmanager
    async def context(
        self,
        user: Optional[Any] = None,
        tenant_id: Optional[Any] = None,
        **context_vars
    ) -> AsyncGenerator[None, None]:
        """
        Execute requests within a context.
        
        Sets user, tenant, and custom context variables for all requests
        within the async with block.
        
        Args:
            user: User object to set in context
            tenant_id: Tenant ID to set in context
            **context_vars: Additional context variables
        
        **Example:**
        
            async with client.context(user=user, tenant_id=tenant.id):
                response = await client.get("/profile")
                # User and tenant_id available in request handlers
        """
        # Store original values
        original_user = get_user()
        original_tenant = get_tenant_id()
        
        try:
            # Set context
            if user:
                set_user(user)
            if tenant_id:
                set_tenant(tenant_id)
            
            # Set additional context vars (direct manipulation)
            tokens = {}
            for key, value in context_vars.items():
                if hasattr(self._context_manager, f'_{key}_ctx'):
                    ctx_var = getattr(self._context_manager, f'_{key}_ctx')
                    tokens[key] = ctx_var.set(value)
            
            yield
        finally:
            # Restore original values
            if original_user:
                set_user(original_user)
            elif user:
                set_user(None)
            
            if original_tenant:
                set_tenant(original_tenant)
            elif tenant_id:
                set_tenant(None)
            
            # Reset custom context vars
            for key, token in tokens.items():
                if hasattr(self._context_manager, f'_{key}_ctx'):
                    ctx_var = getattr(self._context_manager, f'_{key}_ctx')
                    ctx_var.reset(token)


# ============================================================================
# Factories — Create test objects (users, models, etc.)
# ============================================================================


class UserFactory:
    """
    Factory for creating test users.
    
    **Usage:**
    
        # Create user
        user = await user_factory.create(email="test@example.com")
        
        # Create admin
        admin = await user_factory.create_admin()
        
        # Create multiple
        users = [await user_factory.create() for _ in range(5)]
    """
    
    def __init__(self, db: Database, user_model: type):
        """
        Initialize factory.
        
        Args:
            db: Database instance
            user_model: User model class
        """
        self.db = db
        self.user_model = user_model
        self.counter = 0
    
    async def create(
        self,
        email: Optional[str] = None,
        password: str = "testpass123",
        is_staff: bool = False,
        is_active: bool = True,
        **kwargs
    ) -> Any:
        """
        Create a test user.
        
        Args:
            email: User email (auto-generated if not provided)
            password: Plaintext password (auto-hashed)
            is_staff: Whether user is staff
            is_active: Whether user is active
            **kwargs: Additional model fields
        
        Returns:
            Created user instance
        """
        if email is None:
            self.counter += 1
            email = f"testuser{self.counter}@example.com"
        
        # Hash password if hasher is available
        hashed = password
        if HAS_AUTH:
            from eden.auth.backends import PasswordHasher
            hasher = PasswordHasher()
            hashed = hasher.hash(password)
        
        # Create user
        user = await self.user_model.objects.create(
            email=email,
            password=hashed,
            is_staff=is_staff,
            is_active=is_active,
            **kwargs
        )
        
        return user
    
    async def create_admin(self, email: Optional[str] = None, **kwargs) -> Any:
        """Create an admin user."""
        return await self.create(email=email, is_staff=True, **kwargs)
    
    async def create_batch(self, count: int, **kwargs) -> list[Any]:
        """Create multiple users."""
        return [await self.create(**kwargs) for _ in range(count)]


class TenantFactory:
    """
    Factory for creating test tenants (multi-tenancy).
    
    **Usage:**
    
        tenant = await tenant_factory.create(name="Acme Corp")
    """
    
    def __init__(self, db: Database, tenant_model: type):
        """Initialize factory."""
        self.db = db
        self.tenant_model = tenant_model
        self.counter = 0
    
    async def create(self, name: Optional[str] = None, **kwargs) -> Any:
        """
        Create a test tenant.
        
        Args:
            name: Tenant name (auto-generated if not provided)
            **kwargs: Additional model fields
        
        Returns:
            Created tenant instance
        """
        if name is None:
            self.counter += 1
            name = f"TestTenant{self.counter}"
        
        tenant = await self.tenant_model.objects.create(name=name, **kwargs)
        return tenant


class ModelFactory:
    """
    Generic factory for creating model instances.
    
    Useful for creating any model type with defaults.
    
    **Usage:**
    
        factory = ModelFactory(Product)
        product = await factory.create(name="Widget", price=9.99)
    """
    
    def __init__(self, model: type):
        """Initialize with model."""
        self.model = model
    
    async def create(self, **kwargs) -> Any:
        """Create model instance."""
        return await self.model.objects.create(**kwargs)
    
    async def create_batch(self, count: int, **kwargs) -> list[Any]:
        """Create multiple instances."""
        return [await self.create(**kwargs) for _ in range(count)]


# ============================================================================
# Fixtures (only loaded when pytest is available)
# ============================================================================


if HAS_PYTEST:
    @pytest.fixture
    def event_loop():
        """
        Provide event loop for async tests.
        
        Pytest-asyncio integration.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        yield loop
    
    
    @pytest.fixture
    def app() -> Eden:
        """
        Create a fresh Eden app for testing.
        
        Pre-configured for test environment:
        - Debug enabled
        - In-memory database
        - Context isolation
        
        Returns:
            Eden app instance
        """
        app = Eden(title="TestApp", debug=True)
        return app
    
    
    @pytest.fixture
    async def client(app: Eden) -> AsyncGenerator[TestClient, None]:
        """
        Create an async test client.
        
        Manages lifecycle of AsyncClient and test context.
        
        Usage:
            async def test_api(client):
                response = await client.get("/api/endpoint")
                assert response.status_code == 200
        
        Yields:
            TestClient instance
        """
        async with TestClient(app, base_url="http://testserver") as tc:
            yield tc
    
    
    @pytest.fixture
    async def db() -> AsyncGenerator[Database, None]:
        """
        Create an in-memory database for testing.
        
        Auto-creates tables on connection.
        
        Yields:
            Database instance
        """
        database = Database("sqlite+aiosqlite:///:memory:")
        await database.connect(create_tables=True)
        yield database
        await database.disconnect()
    
    
    @pytest.fixture
    async def cleanup_context():
        """
        Clean up context after test.
        
        Ensures context vars are reset between tests.
        """
        yield
        
        # Reset context
        await context_manager.on_request_end()
    
    
    @pytest.fixture
    async def user_factory(db: Database) -> UserFactory:
        """
        Create user factory.
        
        Usage:
            async def test_user(user_factory):
                user = await user_factory.create(email="test@example.com")
                admin = await user_factory.create_admin()
        
        Yields:
            UserFactory instance
        """
        # Import here to avoid circular imports
        try:
            from app.models import User
            return UserFactory(db, User)
        except ImportError:
            # Return mock if User model not available
            return UserFactory(db, None)
    
    
    @pytest.fixture
    async def tenant_factory(db: Database) -> TenantFactory:
        """
        Create tenant factory for multi-tenancy tests.
        
        Yields:
            TenantFactory instance
        """
        try:
            from app.models import Tenant
            return TenantFactory(db, Tenant)
        except ImportError:
            return TenantFactory(db, None)
    
    
    @pytest.fixture
    def mock_stripe():
        """
        Mock Stripe API.
        
        Useful for testing payment flows without hitting real Stripe.
        
        Returns:
            MagicMock stripe module
        """
        mock = MagicMock()
        mock.Charge = MagicMock()
        mock.Charge.create = MagicMock(
            return_value={"id": "ch_test", "status": "succeeded"}
        )
        mock.Customer = MagicMock()
        mock.Customer.create = MagicMock(
            return_value={"id": "cus_test"}
        )
        with patch.dict("sys.modules", {"stripe": mock}):
            yield mock
    
    
    @pytest.fixture
    def mock_email():
        """
        Mock email sending.
        
        Useful for testing email flows without actual SMTP.
        
        Returns:
            MagicMock for email backend
        """
        with patch("eden.mail.send_email") as mock:
            mock.return_value = AsyncMock(return_value=True)
            yield mock
    
    
    @pytest.fixture(autouse=True)
    def mock_s3():
        """
        Mock AWS S3.
        
        Useful for testing file uploads without S3.
        
        Returns:
            MagicMock for S3 client
        """
        try:
            import boto3
        except ImportError:
            mock_boto3 = MagicMock()
            s3_mock = MagicMock()
            s3_mock.put_object = MagicMock(return_value={"ETag": "test"})
            s3_mock.get_object = MagicMock(
                return_value={"Body": MagicMock(read=MagicMock(return_value=b"data"))}
            )
            mock_boto3.client.return_value = s3_mock
            with patch.dict("sys.modules", {"boto3": mock_boto3}):
                yield s3_mock
        else:
            yield None

    @pytest.fixture(autouse=True)
    def mock_optional_dependencies():
        """Automatically mock optional dependencies if they are not installed."""
        mocks = {}
        
        # supabase mock
        try:
            import supabase
        except ImportError:
            mock_sb = MagicMock()
            mock_sb.create_client = MagicMock()
            mocks["supabase"] = mock_sb
            
        # croniter mock
        try:
            import croniter
        except ImportError:
            mock_cron = MagicMock()
            # Test expects croniter(expr, now).get_next(datetime)
            it_mock = MagicMock()
            it_mock.get_next.return_value = datetime.datetime.now()
            mock_cron.return_value = it_mock
            mock_cron.croniter = mock_cron
            mocks["croniter"] = mock_cron
            
        # taskiq mock
        try:
            import taskiq
        except ImportError:
            mock_iq = MagicMock()
            mock_iq.AsyncBroker = MagicMock
            mock_iq.InMemoryBroker = MagicMock
            mocks["taskiq"] = mock_iq
            
        # aioboto3 mock
        try:
            import aioboto3
        except ImportError:
            mock_aio = MagicMock()
            mock_aio.Session = MagicMock()
            mocks["aioboto3"] = mock_aio
            
        if mocks:
            with patch.dict("sys.modules", mocks):
                yield mocks
        else:
            yield {}
    
    
    # ============================================================================
    # Pytest Hooks & Plugins
    # ============================================================================
    
    
    def pytest_configure(config):
        """
        Pytest plugin configuration.
        
        Registers custom markers for test categorization.
        """
        config.addinivalue_line(
            "markers", "integration: Integration tests (hit database, external APIs)"
        )
        config.addinivalue_line(
            "markers", "unit: Unit tests (fast, isolated)"
        )
        config.addinivalue_line(
            "markers", "slow: Slow tests (> 1 second)"
        )
        config.addinivalue_line(
            "markers", "async: Async tests"
        )
    
    
    @pytest.fixture(autouse=True)
    async def reset_global_context():
        """
        Auto-reset context between tests.
        
        Prevents context leaks between test cases.
        """
        await context_manager.on_request_end()
        
        yield
        
        await context_manager.on_request_end()

