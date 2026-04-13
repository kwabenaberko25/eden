"""
Eden Framework Admin Dashboard Routes (Legacy Support)

This file is now deprecated. Admin dashboard is now integrated directly into
the AdminSite.build_router() method in eden/admin/__init__.py.

For new implementations, use:
    from eden.admin import admin
    router = admin.build_router(prefix="/admin")

This file is kept for backward compatibility with existing code that may
import from it directly.
"""

from eden.requests import Request
from eden import Router as APIRouter
from .premium_dashboard import PremiumAdminTemplate
from .flags_panel import FlagsAdminPanel
from eden.flags import get_flag_manager


def get_admin_routes(prefix: str = "/admin") -> APIRouter:
    """
    DEPRECATED: Create router with admin dashboard routes.
    
    Use AdminSite.build_router() instead.
    
    Args:
        prefix: URL prefix for admin routes
        
    Returns:
        FastAPI Router with all admin endpoints
    """
    from eden.responses import HtmlResponse
    from eden.admin import admin as default_admin
    
    # Delegate to the new integrated approach
    return default_admin.build_router(prefix=prefix)


# Export for backward compatibility
__all__ = ["get_admin_routes"]

