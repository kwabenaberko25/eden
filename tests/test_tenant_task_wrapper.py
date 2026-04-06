from eden.tenancy.context import spawn_safe_task, set_current_tenant, get_current_tenant
import asyncio

class DummyTenant:
    pass

async def test_spawn_safe_task_isolation():
    tenant = DummyTenant()
    
    async def _inner_task():
        # Inner task shouldn't inherit context implicitly, but wait, copy_context DOES copy context variables!
        # ContextVars are preserved. So `get_current_tenant()` will return it if not isolated,
        # but wait, wait... spawn_safe_task replicates context by default unless specified differently.
        return get_current_tenant()
    
    token = set_current_tenant(tenant)
    try:
        # spawn_safe_task without isolate=True replicates context
        t1 = spawn_safe_task(_inner_task())
        res1 = await t1
        assert res1 == tenant
        
        # spawn_safe_task with isolate=True starts fresh context
        t2 = spawn_safe_task(_inner_task(), isolate=True)
        res2 = await t2
        assert res2 is None
    finally:
        from eden.tenancy.context import reset_current_tenant
        reset_current_tenant(token)
