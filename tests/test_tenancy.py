import pytest
import uuid
from eden.db import Model, f
from eden.tenancy.models import Tenant
from eden.tenancy.mixins import TenantMixin
from eden.tenancy.context import set_current_tenant, reset_current_tenant

class TenantTask(TenantMixin, Model):
    __tablename__ = "tenant_test_tasks"
    title: str = f(max_length=100)

@pytest.fixture(autouse=True)
async def setup_db(db, db_transaction):
    async with db.engine.begin() as conn:
        await conn.run_sync(Model.metadata.create_all)
    yield

@pytest.fixture
async def tenant_a():
    return await Tenant.create(name="Tenant A", slug="tenant-a")

@pytest.fixture
async def tenant_b():
    return await Tenant.create(name="Tenant B", slug="tenant-b")

@pytest.mark.asyncio
async def test_tenant_creation(tenant_a):
    assert tenant_a.id is not None
    assert tenant_a.name == "Tenant A"
    assert tenant_a.slug == "tenant-a"

@pytest.mark.asyncio
async def test_tenant_isolation(tenant_a, tenant_b):
    # Set context to Tenant A
    token = set_current_tenant(tenant_a)
    try:
        task_a = await TenantTask.create(title="Task A")
        assert task_a.tenant_id == tenant_a.id
        
        # Verify it's visible
        tasks = await TenantTask.all()
        assert len(tasks) == 1
        assert tasks[0].title == "Task A"
        assert tasks[0].id == task_a.id
    finally:
        reset_current_tenant(token)

    # Set context to Tenant B
    token = set_current_tenant(tenant_b)
    try:
        # Task A should NOT be visible to Tenant B
        tasks = await TenantTask.all()
        assert len(tasks) == 0
        
        # Create Task B
        task_b = await TenantTask.create(title="Task B")
        assert task_b.tenant_id == tenant_b.id
        
        # Only Task B visible
        tasks = await TenantTask.all()
        assert len(tasks) == 1
        assert tasks[0].title == "Task B"
        assert tasks[0].id == task_b.id
    finally:
        reset_current_tenant(token)

@pytest.mark.asyncio
async def test_cross_tenant_access_prevention(tenant_a, tenant_b):
    # Create task for Tenant A
    token = set_current_tenant(tenant_a)
    try:
        task_a = await TenantTask.create(title="Task A")
    finally:
        reset_current_tenant(token)
    
    # Try to access as Tenant B
    token = set_current_tenant(tenant_b)
    try:
        # get() uses _base_select() which applies the filter
        fetched = await TenantTask.get(task_a.id)
        assert fetched is None
        
        # filter() should be empty
        filtered = await TenantTask.filter(id=task_a.id).all()
        assert len(filtered) == 0
        
        # count should be 0
        cnt = await TenantTask.filter(id=task_a.id).count()
        assert cnt == 0
    finally:
        reset_current_tenant(token)

@pytest.mark.asyncio
async def test_global_access_no_context(tenant_a, tenant_b):
    # Create tasks for both tenants
    token_a = set_current_tenant(tenant_a)
    try:
        await TenantTask.create(title="Task A")
    finally:
        reset_current_tenant(token_a)
        
    token_b = set_current_tenant(tenant_b)
    try:
        await TenantTask.create(title="Task B")
    finally:
        reset_current_tenant(token_b)
        
    # Query without tenant context (Fail-Secure)
    # The default behavior of TenantMixin._base_select is to enforce isolation
    # and return an empty result if no tenant is found in the context.
    tasks = await TenantTask.all()
    assert len(tasks) == 0

@pytest.mark.asyncio
async def test_manual_tenant_assignment(tenant_a, tenant_b):
    # Even if Tenant B is in context, we can manually assign to Tenant A
    token = set_current_tenant(tenant_b)
    try:
        task = await TenantTask.create(title="Manual", tenant_id=tenant_a.id)
        assert task.tenant_id == tenant_a.id
    finally:
        reset_current_tenant(token)
    
    # Verify Tenant A can see it
    token = set_current_tenant(tenant_a)
    try:
        fetched = await TenantTask.filter(title="Manual").first()
        assert fetched is not None
        assert fetched.tenant_id == tenant_a.id
    finally:
        reset_current_tenant(token)
