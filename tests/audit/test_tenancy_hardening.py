import pytest
import uuid
import os
from eden.db import Model, f
from eden.tenancy.context import set_current_tenant, reset_current_tenant, _tenant_ctx
from eden.tenancy.registry import tenancy_registry
from eden.tenancy.exceptions import TenancyIsolationError

# Define a "Naked" model: has tenant_id but does NOT inherit from TenantMixin
class NakedModel(Model):
    __tablename__ = "naked_models"
    name: str = f()
    tenant_id: uuid.UUID = f(index=True)

def mock_set_tenant(tenant_id):
    return set_current_tenant(tenant_id)

def mock_reset_tenant(token=None):
    if token:
        reset_current_tenant(token)
    else:
        # Emergency reset if token lost
        _tenant_ctx.set(None)

@pytest.mark.asyncio
async def test_naked_model_auto_registration():
    """Verify that models with tenant_id are auto-registered for isolation."""
    assert tenancy_registry.is_isolated(NakedModel) is True

@pytest.mark.asyncio
async def test_naked_model_isolation(db, db_transaction):
    """Verify that a naked model is isolated even without TenantMixin."""
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()

    # 1. Create data for Tenant A
    token = mock_set_tenant(tenant_a)
    await NakedModel.create(name="Item A", tenant_id=tenant_a)
    mock_reset_tenant(token)
    
    # 2. Create data for Tenant B
    token = mock_set_tenant(tenant_b)
    await NakedModel.create(name="Item B", tenant_id=tenant_b)
    mock_reset_tenant(token)
    
    # 3. Query as Tenant A
    token = mock_set_tenant(tenant_a)
    items = await NakedModel.all()
    assert len(items) == 1
    assert items[0].name == "Item A"
    mock_reset_tenant(token)
    
    # 4. Query as Tenant B
    token = mock_set_tenant(tenant_b)
    items = await NakedModel.all()
    assert len(items) == 1
    assert items[0].name == "Item B"
    mock_reset_tenant(token)
    
    # 5. Query without tenant (Fail-Secure)
    mock_reset_tenant()
    items = await NakedModel.all()
    assert len(items) == 0

@pytest.mark.asyncio
async def test_strict_tenancy_enforcement(db):
    """Verify that strict mode raises TenancyIsolationError."""
    # Enable strict mode
    tenancy_registry.enable_strict_mode(True)
    try:
        mock_reset_tenant()
        
        # This should raise TenancyIsolationError because no tenant is set
        with pytest.raises(TenancyIsolationError) as exc:
            await NakedModel.all()
        
        assert "Attempted to query tenant-isolated model NakedModel" in str(exc.value)
    finally:
        # Disable strict mode for other tests
        tenancy_registry.enable_strict_mode(False)

@pytest.mark.asyncio
async def test_bypass_isolation(db, db_transaction):
    """Verify that we can still bypass isolation when needed."""
    tenant_a = uuid.uuid4()
    token = mock_set_tenant(tenant_a)
    await NakedModel.create(name="Global Item", tenant_id=tenant_a)
    
    mock_reset_tenant(token)
    # Should see 0 with normal query
    assert len(await NakedModel.all()) == 0
    
    # Should see 1 with bypass
    items = await NakedModel.query().include_tenantless().all()
    assert len(items) >= 1 # Might have items from previous tests if not isolated
