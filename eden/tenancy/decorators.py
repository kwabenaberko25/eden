"""
Eden — Tenancy Route Decorators

Provides routing decorators to enforce tenant boundaries and access control
on a per-route basis.
"""

from functools import wraps
from typing import Any, Callable

from eden.exceptions import Forbidden
from eden.tenancy.context import get_current_tenant


def tenant_required(allow_anonymous: bool = False) -> Callable:
    """
    Route decorator to enforce that a request executes within an active tenant context.

    If no tenant is active in the context, this decorator raises a 403 Forbidden.
    
    Args:
        allow_anonymous: If True, allows the request to proceed without a tenant.

    Example:
        @app.route("/api/invoices")
        @tenant_required()
        async def list_invoices(request):
            ...
            
        @app.route("/api/public-or-tenant")
        @tenant_required(allow_anonymous=True)
        async def public_api(request):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            tenant = get_current_tenant()
            if not tenant and not allow_anonymous:
                raise Forbidden("This route requires an active tenant context.")
            return await func(*args, **kwargs)
        return wrapper

    # Support for using decorator both with and without parens:
    # @tenant_required
    # vs
    # @tenant_required(allow_anonymous=True)
    if callable(allow_anonymous):
        func = allow_anonymous
        allow_anonymous = False
        return decorator(func)

    return decorator
