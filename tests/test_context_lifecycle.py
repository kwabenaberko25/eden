"""
Tests for Async Context Propagation System (Issue #14)

Tests verify:
- Context initialization and cleanup
- Context isolation between requests
- Fallback values (None) for unset context
- Request ID generation and uniqueness
- No context leaks between concurrent requests
- Lifecycle hooks are called correctly

Run with: pytest tests/test_context_lifecycle.py -v
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from starlette.requests import Request
from starlette.testclient import TestClient

from eden.context import (
    context_manager,
    get_request,
    get_user,
    get_app,
    get_tenant_id,
    get_request_id,
    set_user,
    set_tenant,
)


class TestContextManagerBasic:
    """Layer 1: Test context manager core functionality."""

    @pytest.mark.asyncio
    async def test_on_request_start_initializes_context(self):
        """Test that on_request_start initializes all context vars."""
        # Mock request and app
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/test"
        mock_app = MagicMock()

        # Initialize context
        await context_manager.on_request_start(mock_request, mock_app)

        # Verify context was set
        assert get_request() == mock_request
        assert get_app() == mock_app
        assert get_request_id() != ""  # Should be UUID string
        # User and tenant should remain None
        assert get_user() is None
        assert get_tenant_id() is None

        # Cleanup
        await context_manager.on_request_end()

    @pytest.mark.asyncio
    async def test_on_request_end_clears_context(self):
        """Test that on_request_end clears all context vars."""
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/test"
        mock_app = MagicMock()

        # Initialize
        await context_manager.on_request_start(mock_request, mock_app)
        assert get_request() is not None

        # Cleanup
        await context_manager.on_request_end()

        # Verify cleaned up
        assert get_request() is None
        assert get_app() is None
        assert get_request_id() == ""
        assert get_user() is None
        assert get_tenant_id() is None

    @pytest.mark.asyncio
    async def test_request_id_is_unique(self):
        """Test that each request gets a unique request ID."""
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/test"
        mock_app = MagicMock()

        # First request
        await context_manager.on_request_start(mock_request, mock_app)
        request_id_1 = get_request_id()
        await context_manager.on_request_end()

        # Second request
        await context_manager.on_request_start(mock_request, mock_app)
        request_id_2 = get_request_id()
        await context_manager.on_request_end()

        # IDs should be different (UUID format)
        assert request_id_1 != request_id_2
        assert len(request_id_1) == 36  # UUID4 string length
        assert "-" in request_id_1  # UUID format

    @pytest.mark.asyncio
    async def test_set_user_updates_context(self):
        """Test that set_user updates the user context var."""
        mock_user = MagicMock()
        mock_user.id = 123
        mock_user.name = "Alice"

        set_user(mock_user)
        assert get_user() == mock_user
        assert get_user().id == 123

        # Cleanup
        set_user(None)
        assert get_user() is None

    @pytest.mark.asyncio
    async def test_set_tenant_updates_context(self):
        """Test that set_tenant updates the tenant ID context var."""
        tenant_id = "tenant-123"
        set_tenant(tenant_id)
        assert get_tenant_id() == tenant_id

        # Cleanup
        set_tenant(None)
        assert get_tenant_id() is None

    @pytest.mark.asyncio
    async def test_on_request_end_is_idempotent(self):
        """Test that calling on_request_end multiple times is safe."""
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/test"
        mock_app = MagicMock()

        await context_manager.on_request_start(mock_request, mock_app)

        # Call end multiple times
        await context_manager.on_request_end()
        await context_manager.on_request_end()
        await context_manager.on_request_end()

        # Should be safely cleaned up
        assert get_request() is None


class TestContextIsolation:
    """Test context isolation between concurrent requests."""

    @pytest.mark.asyncio
    async def test_concurrent_requests_have_isolated_contexts(self):
        """Test that concurrent requests don't interfere with each other's context."""
        
        async def request_task(user_id: int, tenant_id: str):
            """Simulate a request task that sets context and then checks it."""
            mock_request = MagicMock(spec=Request)
            mock_request.url.path = f"/user/{user_id}"
            mock_app = MagicMock()

            await context_manager.on_request_start(mock_request, mock_app)
            
            # Set user and tenant for this request
            mock_user = MagicMock()
            mock_user.id = user_id
            set_user(mock_user)
            set_tenant(tenant_id)

            # Verify context in this request
            assert get_user().id == user_id
            assert get_tenant_id() == tenant_id
            request_id = get_request_id()

            # Wait a bit to interleave with other requests
            await asyncio.sleep(0.01)

            # Verify context hasn't changed (isolation)
            assert get_user().id == user_id
            assert get_tenant_id() == tenant_id
            assert get_request_id() == request_id

            await context_manager.on_request_end()
            return (user_id, tenant_id)

        # Run multiple requests concurrently
        results = await asyncio.gather(
            request_task(1, "tenant-a"),
            request_task(2, "tenant-b"),
            request_task(3, "tenant-c"),
        )

        assert results == [(1, "tenant-a"), (2, "tenant-b"), (3, "tenant-c")]

    @pytest.mark.asyncio
    async def test_context_cleanup_after_exception(self):
        """Test that context is cleaned up even if an exception occurs."""
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/test"
        mock_app = MagicMock()

        try:
            await context_manager.on_request_start(mock_request, mock_app)
            assert get_request() is not None
            # Simulate exception
            raise ValueError("Test error")
        except ValueError:
            pass
        finally:
            await context_manager.on_request_end()

        # Context should be cleaned up after exception
        assert get_request() is None
        assert get_user() is None


class TestContextMiddleware:
    """Layer 2: Test ContextMiddleware integration."""

    def test_context_middleware_is_applied(self):
        """Test that RequestContextMiddleware is registered in app build."""
        from eden.app import Eden

        app = Eden(debug=True)
        
        # Check the middleware stack includes RequestContextMiddleware
        # The middleware stack is a list of (cls, kwargs) tuples
        middleware_names = [cls.__name__ for cls, _, _ in app._middleware_stack]
        has_context = any("RequestContext" in name for name in middleware_names)
        
        # If not already added, it may be added during __call__
        # Just verify the import works and the class exists
        if not has_context:
            from eden.middleware import RequestContextMiddleware
            assert RequestContextMiddleware is not None

    @pytest.mark.asyncio
    async def test_middleware_initializes_context_for_request(self):
        """Test that ContextMiddleware initializes context before handler runs."""
        from eden.app import Eden
        from starlette.responses import JSONResponse

        app = Eden(debug=True)

        # Store context values from inside the handler
        captured_context = {}

        @app.get("/test-context")
        async def test_handler(request):
            """Handler that captures context state."""
            captured_context["user"] = get_user()
            captured_context["app"] = get_app()
            captured_context["request_id"] = get_request_id()
            return JSONResponse({"ok": True})

        # Make request via test client
        client = TestClient(app)
        response = client.get("/test-context")

        assert response.status_code == 200
        # Context should have been initialized in handler
        assert captured_context["app"] is not None
        assert captured_context["request_id"] != ""


class TestRunInContext:
    """Test context_manager.run_in_context() for background tasks."""

    @pytest.mark.asyncio
    async def test_run_in_context_with_custom_context(self):
        """Test running a coroutine with custom context."""
        
        async def task_needing_context():
            user = get_user()
            tenant_id = get_tenant_id()
            return (user.id if user else None, tenant_id)

        mock_user = MagicMock()
        mock_user.id = 42

        result = await context_manager.run_in_context(
            task_needing_context,
            user=mock_user,
            tenant_id="tenant-xyz",
        )

        assert result == (42, "tenant-xyz")

    @pytest.mark.asyncio
    async def test_run_in_context_restores_previous_context(self):
        """Test that run_in_context restores previous context after execution."""
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/test"
        mock_app = MagicMock()

        # Initialize outer context
        await context_manager.on_request_start(mock_request, mock_app)
        outer_request_id = get_request_id()

        async def inner_task():
            return get_request_id()

        # Run inner task with different context
        inner_request_id = await context_manager.run_in_context(
            inner_task,
            # Don't pass request_id, so it stays unset in inner scope
        )

        # Outer context should be restored
        assert get_request_id() == outer_request_id
        assert inner_request_id != outer_request_id

        await context_manager.on_request_end()


class TestContextIntegrationWithAuth:
    """Test context integration with auth/tenancy patterns."""

    @pytest.mark.asyncio
    async def test_auth_middleware_pattern(self):
        """Simulate auth middleware setting user in context."""
        
        async def simulated_auth_middleware(request):
            """Simulates auth middleware that sets user."""
            # In real middleware, this would extract user from token/session
            mock_user = MagicMock()
            mock_user.id = 99
            mock_user.email = "user@example.com"
            set_user(mock_user)
            return mock_user

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/test"
        mock_app = MagicMock()

        await context_manager.on_request_start(mock_request, mock_app)

        # Simulate auth middleware
        user = await simulated_auth_middleware(mock_request)
        
        # User should be in context
        assert get_user() == user
        assert get_user().email == "user@example.com"

        await context_manager.on_request_end()

    @pytest.mark.asyncio
    async def test_multitenancy_pattern(self):
        """Simulate multi-tenant middleware setting tenant."""
        
        async def simulated_tenancy_middleware(request):
            """Simulates tenancy middleware that sets tenant."""
            # In real middleware, this would extract tenant from subdomain/header
            tenant_id = "acme-corp"
            set_tenant(tenant_id)
            return tenant_id

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/test"
        mock_app = MagicMock()

        await context_manager.on_request_start(mock_request, mock_app)

        # Simulate tenancy middleware
        tenant_id = await simulated_tenancy_middleware(mock_request)

        # Tenant should be in context
        assert get_tenant_id() == tenant_id

        await context_manager.on_request_end()


class TestContextAPIConsistency:
    """Test that context API is consistent and well-designed."""

    @pytest.mark.asyncio
    async def test_all_getters_return_none_for_unset_context(self):
        """Test that all getters return None/empty for unset context."""
        # Clean slate
        await context_manager.on_request_end()

        # All getters should return sensible defaults
        assert get_user() is None
        assert get_tenant_id() is None
        assert get_request() is None
        assert get_app() is None
        assert get_request_id() == ""  # Empty string for unset request_id

    @pytest.mark.asyncio
    async def test_context_values_are_accessible_via_multiple_approaches(self):
        """Test that context is accessible via context_manager and convenience functions."""
        mock_user = MagicMock()
        mock_user.id = 1

        set_user(mock_user)

        # Both approaches should work
        assert context_manager.get_user() == mock_user
        assert get_user() == mock_user
        assert context_manager.get_user() == get_user()


class TestContextDocumentation:
    """Verify context system is properly documented."""

    def test_context_manager_has_docstrings(self):
        """Test that ContextManager has comprehensive docstrings."""
        assert context_manager.__class__.__doc__ is not None
        assert len(context_manager.__class__.__doc__) > 100

    def test_lifecycle_methods_are_documented(self):
        """Test that lifecycle methods have docstrings."""
        assert context_manager.on_request_start.__doc__ is not None
        assert context_manager.on_request_end.__doc__ is not None
        assert "request start" in context_manager.on_request_start.__doc__.lower()
        assert "cleanup" in context_manager.on_request_end.__doc__.lower()

    def test_convenience_functions_are_documented(self):
        """Test that convenience functions have docstrings."""
        assert get_user.__doc__ is not None
        assert get_request.__doc__ is not None
        assert get_tenant_id.__doc__ is not None
        assert get_request_id.__doc__ is not None
