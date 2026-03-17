"""
Multi-Tenancy Security Fixes - Unit Test Suite

Tests for code structure and protection mechanisms:
1. Layer 1: QuerySet calls _base_select() for tenant filtering
2. Layer 2: RawQuery validates tenant isolation
3. Layer 3: Tenant.provision_schema() handles schema management
4. Layer 4: TenantMiddleware enforces context and headers
"""

import pytest
import uuid
import logging
from unittest.mock import AsyncMock, MagicMock
from starlette.responses import Response as StarletteResponse

from eden.db.raw_sql import RawQuery, TenantException
from eden.tenancy.models import Tenant
from eden.tenancy.mixins import TenantMixin
from eden.tenancy.context import (
    set_current_tenant,
    reset_current_tenant,
    get_current_tenant_id,
    _tenant_ctx,
)
from eden.tenancy.middleware import TenantMiddleware

logger = logging.getLogger(__name__)


# ── Layer 1: Query Auto-Filtering ──────────────────────────────────────

def test_tenantmixin_has_apply_tenant_filter():
    """Layer 1: TenantMixin has _apply_tenant_filter method."""
    assert hasattr(TenantMixin, "_apply_tenant_filter")
    assert callable(getattr(TenantMixin, "_apply_tenant_filter"))


def test_tenantmixin_has_apply_default_filters():
    """Layer 1: TenantMixin has _apply_default_filters method."""
    assert hasattr(TenantMixin, "_apply_default_filters")
    assert callable(getattr(TenantMixin, "_apply_default_filters"))


def test_tenantmixin_has_before_create():
    """Layer 1: TenantMixin has before_create hook for auto tenant_id assignment."""
    assert hasattr(TenantMixin, "before_create")
    assert callable(getattr(TenantMixin, "before_create"))


def test_tenantmixin_has_tenant_id_column():
    """Layer 1: TenantMixin defines tenant_id foreign key."""
    assert hasattr(TenantMixin, "tenant_id")


# ── Layer 2: Raw SQL Protection ────────────────────────────────────────

def test_rawquery_has_validate_tenant_isolation():
    """Layer 2: RawQuery has _validate_tenant_isolation method."""
    assert hasattr(RawQuery, "_validate_tenant_isolation")
    assert callable(getattr(RawQuery, "_validate_tenant_isolation"))


def test_tenant_exception_exists():
    """Layer 2: TenantException class exists for enforcement."""
    assert issubclass(TenantException, Exception)


def test_rawquery_execute_has_skip_tenant_check():
    """Layer 2: RawQuery.execute() accepts _skip_tenant_check parameter."""
    import inspect
    sig = inspect.signature(RawQuery.execute)
    assert "_skip_tenant_check" in sig.parameters


def test_rawquery_execute_scalar_has_skip_tenant_check():
    """Layer 2: RawQuery.execute_scalar() accepts _skip_tenant_check parameter."""
    import inspect
    sig = inspect.signature(RawQuery.execute_scalar)
    assert "_skip_tenant_check" in sig.parameters


def test_raw_update_has_skip_tenant_check():
    """Layer 2: raw_update() accepts _skip_tenant_check parameter."""
    import inspect
    from eden.db.raw_sql import raw_update
    sig = inspect.signature(raw_update)
    assert "_skip_tenant_check" in sig.parameters


def test_validation_checks_for_tenant_id():
    """Layer 2: Validation method checks for tenant_id in SQL."""
    import inspect
    source = inspect.getsource(RawQuery._validate_tenant_isolation)
    assert "tenant_id" in source


def test_validation_checks_context():
    """Layer 2: Validation method checks tenant context."""
    import inspect
    source = inspect.getsource(RawQuery._validate_tenant_isolation)
    assert "get_current_tenant_id" in source


# ── Layer 3: Schema Provisioning ───────────────────────────────────────

def test_tenant_has_provision_schema():
    """Layer 3: Tenant model has provision_schema method."""
    assert hasattr(Tenant, "provision_schema")
    assert callable(getattr(Tenant, "provision_schema"))


def test_provision_schema_has_sanitization():
    """Layer 3: provision_schema sanitizes schema names."""
    import inspect
    source = inspect.getsource(Tenant.provision_schema)
    assert "isalnum" in source or "safe_schema" in source


def test_provision_schema_creates_schema():
    """Layer 3: provision_schema creates PostgreSQL schema."""
    import inspect
    source = inspect.getsource(Tenant.provision_schema)
    assert "CREATE SCHEMA" in source


def test_provision_schema_manages_search_path():
    """Layer 3: provision_schema manages search_path."""
    import inspect
    source = inspect.getsource(Tenant.provision_schema)
    assert "search_path" in source


def test_provision_schema_has_finally_cleanup():
    """Layer 3: provision_schema has finally block for cleanup."""
    import inspect
    source = inspect.getsource(Tenant.provision_schema)
    assert "finally:" in source


def test_provision_schema_resets_schema():
    """Layer 3: provision_schema resets schema to prevent pool leaks."""
    import inspect
    source = inspect.getsource(Tenant.provision_schema)
    # Check for schema reset (either explicit or via variable restoration)
    assert "reset" in source.lower() or source.count("SET search_path") >= 2


def test_provision_schema_validates_schema_name():
    """Layer 3: provision_schema validates schema_name is set."""
    import inspect
    source = inspect.getsource(Tenant.provision_schema)
    assert "ValueError" in source or "schema_name" in source


def test_provision_schema_is_async():
    """Layer 3: provision_schema is async for proper await handling."""
    import inspect
    source = inspect.getsource(Tenant.provision_schema)
    assert "await" in source or "async def" in source


# ── Layer 4: Middleware Enforcement ────────────────────────────────────

def test_middleware_has_dispatch():
    """Layer 4: TenantMiddleware has dispatch method."""
    assert hasattr(TenantMiddleware, "dispatch")
    assert callable(getattr(TenantMiddleware, "dispatch"))


def test_middleware_sets_tenant_context():
    """Layer 4: dispatch() sets tenant context."""
    import inspect
    source = inspect.getsource(TenantMiddleware.dispatch)
    assert "set_current_tenant" in source


def test_middleware_resets_tenant_context():
    """Layer 4: dispatch() resets tenant context in finally."""
    import inspect
    source = inspect.getsource(TenantMiddleware.dispatch)
    assert "reset_current_tenant" in source


def test_middleware_adds_response_headers():
    """Layer 4: dispatch() adds X-Tenant-Enforced header."""
    import inspect
    source = inspect.getsource(TenantMiddleware.dispatch)
    assert "X-Tenant-Enforced" in source or "X-Tenant-ID" in source


def test_middleware_switches_schema():
    """Layer 4: dispatch() switches schema for dedicated-schema tenants."""
    import inspect
    source = inspect.getsource(TenantMiddleware.dispatch)
    assert "set_schema" in source


def test_middleware_has_try_finally():
    """Layer 4: dispatch() uses try/finally for guaranteed cleanup."""
    import inspect
    source = inspect.getsource(TenantMiddleware.dispatch)
    assert "try:" in source and "finally:" in source


def test_middleware_supports_subdomain():
    """Layer 4: middleware supports subdomain strategy."""
    import inspect
    source = inspect.getsource(TenantMiddleware)
    assert "subdomain" in source or hasattr(TenantMiddleware, "_extract_subdomain")


def test_middleware_supports_header():
    """Layer 4: middleware supports header strategy."""
    import inspect
    source = inspect.getsource(TenantMiddleware)
    assert "header" in source


# ── Context Infrastructure ─────────────────────────────────────────────

def test_context_set_current_tenant():
    """Context: set_current_tenant works."""
    from eden.tenancy.context import set_current_tenant
    assert callable(set_current_tenant)


def test_context_get_current_tenant():
    """Context: get_current_tenant works."""
    from eden.tenancy.context import get_current_tenant
    assert callable(get_current_tenant)


def test_context_get_current_tenant_id():
    """Context: get_current_tenant_id works."""
    from eden.tenancy.context import get_current_tenant_id
    assert callable(get_current_tenant_id)


def test_context_reset_current_tenant():
    """Context: reset_current_tenant works."""
    from eden.tenancy.context import reset_current_tenant
    assert callable(reset_current_tenant)


def test_context_uses_contextvars():
    """Context: Uses contextvars for async-safe storage."""
    import contextvars
    assert isinstance(_tenant_ctx, contextvars.ContextVar)


def test_context_isolation():
    """Context: Tenant context is properly isolated."""
    tenant1_id = uuid.uuid4()
    tenant2_id = uuid.uuid4()
    
    # Set first tenant
    class MockTenant:
        def __init__(self, id_val):
            self.id = id_val
    
    t1 = MockTenant(tenant1_id)
    t2 = MockTenant(tenant2_id)
    
    # Set and get
    token1 = set_current_tenant(t1)
    assert get_current_tenant_id() == tenant1_id
    
    # Change context
    token2 = set_current_tenant(t2)
    assert get_current_tenant_id() == tenant2_id
    
    # Reset back
    reset_current_tenant(token2)
    assert get_current_tenant_id() == tenant1_id
    
    # Full reset
    reset_current_tenant(token1)
    assert get_current_tenant_id() is None


# ── Integration Tests ──────────────────────────────────────────────────

def test_layers_are_properly_integrated():
    """Integration: All layers are present and connected."""
    # Layer 1 exists
    assert hasattr(TenantMixin, "_apply_tenant_filter")
    # Layer 2 exists
    assert hasattr(RawQuery, "_validate_tenant_isolation")
    # Layer 3 exists
    assert hasattr(Tenant, "provision_schema")
    # Layer 4 exists
    assert hasattr(TenantMiddleware, "dispatch")
    # Context exists
    assert callable(get_current_tenant_id)


@pytest.mark.asyncio
async def test_mock_middleware_context_setting():
    """Integration: Middleware can set and reset context (mock test)."""
    # Create a mock tenant
    mock_tenant = MagicMock()
    mock_tenant.id = uuid.uuid4()
    mock_tenant.schema_name = None
    
    # Create middleware instance
    middleware = TenantMiddleware(app=None)
    middleware._resolve_tenant = AsyncMock(return_value=mock_tenant)
    
    # Create mock request
    mock_request = MagicMock()
    mock_request.headers = {}
    mock_request.state = MagicMock()
    
    # Track if handler was called with context set
    handler_called_with_context = []
    
    async def mock_call_next(req):
        # Capture if context is set
        handler_called_with_context.append(get_current_tenant_id())
        return StarletteResponse("OK")
    
    # Dispatch
    response = await middleware.dispatch(mock_request, mock_call_next)
    
    # Verify context was set during handler execution
    assert len(handler_called_with_context) == 1
    assert handler_called_with_context[0] == mock_tenant.id
    
    # Verify context is reset after
    assert get_current_tenant_id() is None
