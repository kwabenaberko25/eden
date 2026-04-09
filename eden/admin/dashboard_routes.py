"""
Eden Framework Admin Dashboard Routes

Integrates the self-contained admin UI into FastAPI.

Usage:
    from eden.admin.dashboard_routes import get_admin_routes
    
    app = FastAPI()
    app.include_router(get_admin_routes())
"""

from eden.requests import Request
from eden import Router as APIRouter, App as FastAPI
from pathlib import Path
import os

from .dashboard_template import AdminDashboardTemplate
from .flags_panel import FlagsAdminPanel
from eden.flags import get_flag_manager


def get_admin_routes(prefix: str = "/admin") -> APIRouter:
    """
    Create router with admin dashboard routes.
    
    Args:
        prefix: URL prefix for admin routes
        
    Returns:
        FastAPI Router with all admin endpoints
    """
    from eden.responses import HtmlResponse
    
    router = APIRouter(prefix=prefix)
    panel = FlagsAdminPanel(manager=get_flag_manager())
    
    # Main dashboard page
    @router.get("/")
    async def admin_dashboard(request: Request):
        """Serve self-contained admin dashboard."""
        html = AdminDashboardTemplate.render(
            api_base=f"{prefix}/flags",
            app_name="Eden Framework"
        )
        return HtmlResponse(html)
    
    @router.get("/dashboard")
    async def admin_dashboard_explicit(request: Request):
        """Alias for main dashboard."""
        html = AdminDashboardTemplate.render(
            api_base=f"{prefix}/flags",
            app_name="Eden Framework"
        )
        return HtmlResponse(html)
    
    # Include the panel's built-in routes for flags API
    router.include_router(panel.router, prefix="/flags")
    
    return router


# Export for convenience
__all__ = ["get_admin_routes", "AdminDashboardTemplate"]
