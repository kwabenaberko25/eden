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
