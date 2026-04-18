"""
Eden — Multi-Tenancy Context

ContextVar-based tenant storage for async-safe tenant isolation.
"""

import contextvars
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from eden.tenancy.models import Tenant

# Context variables
_tenant_ctx: contextvars.ContextVar[Any | None] = contextvars.ContextVar(
    "current_tenant", default=None
)

_across_tenants_ctx: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "across_tenants", default=False
)


def set_current_tenant(tenant: "Tenant") -> contextvars.Token:
    """Set the current tenant in context."""
    return _tenant_ctx.set(tenant)


def get_current_tenant() -> Optional["Tenant"]:
    """Get the current tenant from context."""
    return _tenant_ctx.get()


import uuid

def get_current_tenant_id() -> Optional[uuid.UUID]:
    """Get the current tenant's ID from context."""
    val = _tenant_ctx.get()
    if val is None:
        # Fallback to user's active org if no explicit tenant set (Eden Secure-by-Default)
        try:
            from eden.context import get_user
            user = get_user()
            if user and hasattr(user, "active_org_id"):
                val = user.active_org_id
        except (ImportError, AttributeError):
            pass
            
    if val is None:
        return None
    
    # If it's a Tenant instance (B3/B4 compat)
    if hasattr(val, "id"):
        return val.id
        
    # Assume it's a UUID or string already
    if isinstance(val, str):
        try:
            return uuid.UUID(val)
        except ValueError:
            return val
    return val


def reset_current_tenant(token: contextvars.Token) -> None:
    """Reset the tenant context."""
    _tenant_ctx.reset(token)


class AcrossTenants:
    """
    Context manager to perform queries across all tenants.
    Temporarily disables tenant-level scoping while inside the block.
    
    Example:
        async with AcrossTenants():
            total = await Invoice.sum("amount")
    """

    def __init__(self):
        self._token: Optional[contextvars.Token] = None

    def __enter__(self):
        self._token = _across_tenants_ctx.set(True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._token:
            _across_tenants_ctx.reset(self._token)

    async def __aenter__(self):
        return self.__enter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return self.__exit__(exc_type, exc_val, exc_tb)


def is_across_tenants() -> bool:
    """Check if the current context is running 'Across Tenants'."""
    return _across_tenants_ctx.get()


# ── Context-Aware Task Spawning ──────────────────────────────────────────────


def spawn_safe_task(
    coro_or_func,
    *args,
    isolate: bool = False,
    name: str | None = None,
    **kwargs
) -> "asyncio.Task":
    """
    Spawn an asyncio.Task with eagerly-captured Eden context.

    Solves the async tenant-bleeding problem: when a parent request's ``finally``
    block resets tenant/session context variables, a child task spawned via bare
    ``asyncio.create_task()`` may observe stale or ``None`` context values.

    This wrapper **snapshots** all Eden-critical context variables at call time
    and **re-injects** them into the child coroutine before execution begins.
    """
    import asyncio
    from eden.context import context_manager

    # ── Eagerly capture context at spawn time ────────────────────────
    snapshot = {} if isolate else context_manager.get_context_snapshot()

    async def _context_wrapper():
        """
        Re-inject captured context into the child task's execution frame.
        """
        with context_manager.baked_context(snapshot):
            if callable(coro_or_func):
                return await coro_or_func(*args, **kwargs)
            else:
                return await coro_or_func

    # Create task. 
    task = asyncio.create_task(_context_wrapper(), name=name)
    
    # Store reference to prevent garbage collection until the task executes
    def _on_done(f):
        if f.cancelled():
            try:
                coro = f.get_coro()
                if coro:
                    coro.close()
            except Exception:
                pass
                
        if not callable(coro_or_func) and hasattr(coro_or_func, "close"):
            if f.cancelled():
                try:
                    coro_or_func.close()
                except Exception:
                    pass

    task.add_done_callback(_on_done)
    return task
