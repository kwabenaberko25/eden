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
    coro,
    *,
    isolate: bool = False,
    name: str | None = None,
) -> "asyncio.Task":
    """
    Spawn an asyncio.Task with eagerly-captured Eden context.

    Solves the async tenant-bleeding problem: when a parent request's ``finally``
    block resets tenant/session context variables, a child task spawned via bare
    ``asyncio.create_task()`` may observe stale or ``None`` context values.

    This wrapper **snapshots** all Eden-critical context variables at call time
    and **re-injects** them into the child coroutine before execution begins.

    Args:
        coro: The awaitable coroutine to schedule.
        isolate: If ``True``, the task runs deliberately without tenant/session
                 context. Use this for infrastructure tasks (heartbeat, metrics
                 sync, pub/sub listeners) that genuinely do not need tenancy.
                 Documents intent and prevents false-positive audit warnings.
        name: Optional name for the created ``asyncio.Task`` (aids debugging).

    Returns:
        The created ``asyncio.Task`` instance.

    Example — tenant-aware background job::

        from eden.tenancy.context import spawn_safe_task

        async def send_invoice_email(invoice_id: str):
            ...  # This will see the correct tenant DB schema

        spawn_safe_task(send_invoice_email(invoice.id))

    Example — infrastructure task (no tenant needed)::

        spawn_safe_task(self._heartbeat_loop(), isolate=True, name="ws-heartbeat")
    """
    import asyncio

    if isolate:
        # Infrastructure task: deliberately no context propagation.
        # Standard create_task still copies the current Context snapshot,
        # but we document the intent explicitly.
        return asyncio.create_task(coro, name=name)

    # ── Eagerly capture context at spawn time ────────────────────────
    # These values are read NOW, before the parent's finally block runs.
    tenant_snapshot = _tenant_ctx.get()
    across_snapshot = _across_tenants_ctx.get()

    # Session context lives in eden.db.session — import lazily to avoid
    # circular imports at module load time.
    from eden.db.session import _session_context
    session_snapshot = _session_context.get()

    async def _context_wrapper():
        """
        Re-inject captured context into the child task's execution frame.

        Uses ContextVar.set() to install the snapshot, and .reset() in finally
        to avoid leaking state if the task is cancelled or errors out.
        """
        t_token = _tenant_ctx.set(tenant_snapshot)
        a_token = _across_tenants_ctx.set(across_snapshot)
        s_token = _session_context.set(session_snapshot)
        try:
            return await coro
        finally:
            _tenant_ctx.reset(t_token)
            _across_tenants_ctx.reset(a_token)
            _session_context.reset(s_token)

    return asyncio.create_task(_context_wrapper(), name=name)
