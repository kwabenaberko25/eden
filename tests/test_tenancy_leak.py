import pytest
import uuid
import asyncio
from eden.context import context_manager, get_tenant_id
from eden.tenancy.context import get_current_tenant_id

@pytest.mark.asyncio
async def test_tenancy_context_leak_fixed():
    """Test that tenancy context is properly reset across requests (FIXED)."""
    # Simulate first request setting tenant
    tenant_id_1 = "tenant-1"
    context_manager.set_tenant(tenant_id_1)
    
    # Verify it's set in both
    assert get_tenant_id() == tenant_id_1
    # get_current_tenant_id returns UUID if it can be parsed
    current_tid = get_current_tenant_id()
    assert str(current_tid) == tenant_id_1
    
    # End first request
    await context_manager.on_request_end()
    
    # Verify cleanup in BOTH contexts
    assert get_tenant_id() is None, "eden.context._tenant_id_ctx not reset!"
    assert get_current_tenant_id() is None, "eden.tenancy.context._tenant_ctx still leaked!"

@pytest.mark.asyncio
async def test_cross_request_isolation():
    """Verify isolation between simulated requests."""
    # Request 1
    context_manager.set_tenant("tenant-1")
    await context_manager.on_request_end()
    
    # Request 2 (e.g. public request with no tenant)
    assert get_current_tenant_id() is None, "Context leaked from Request 1 to Request 2"
    
    # Request 3 (different tenant)
    context_manager.set_tenant("tenant-2")
    assert str(get_current_tenant_id()) == "tenant-2"
    await context_manager.on_request_end()
    assert get_current_tenant_id() is None
