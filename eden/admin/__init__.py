"""
Eden — Admin Panel

Auto-generated admin interface for managing Model data.
"""

from typing import Any, Optional

from eden.admin.options import ModelAdmin
from eden.routing import Router


class AdminSite:
    """
    Registry for admin-registered models.

    Generates CRUD views and a dashboard for all registered models.

    Usage:
        from eden.admin import admin, ModelAdmin

        class UserAdmin(ModelAdmin):
            list_display = ["email", "full_name", "is_active"]
            search_fields = ["email", "full_name"]

        admin.register(User, UserAdmin)

        # In your app setup:
        app.mount_admin()
    """

    def __init__(self):
        self._registry: dict[type, ModelAdmin] = {}

    def register(self, model: type, admin_class: type | None = None):
        """
        Register a model for the admin panel.

        Can be used as a decorator or called directly:

            # As decorator
            @admin.register
            class User(Model):
                ...

            # Direct call
            admin.register(User, UserAdmin)
        """
        if admin_class is None:
            # Check if model is actually a ModelAdmin subclass (used as decorator)
            if isinstance(model, type) and not issubclass(model, ModelAdmin):
                self._registry[model] = ModelAdmin()
                return model
            admin_class = ModelAdmin

        if isinstance(admin_class, type):
            self._registry[model] = admin_class()
        else:
            self._registry[model] = admin_class
        return model

    def unregister(self, model: type) -> None:
        """Remove a model from the admin registry."""
        self._registry.pop(model, None)

    def is_registered(self, model: type) -> bool:
        """Check if a model is registered."""
        return model in self._registry

    def get_registry(self) -> dict[type, ModelAdmin]:
        """Get all registered models and their admins."""
        return dict(self._registry)

    def build_router(self, prefix: str = "/admin") -> Router:
        """
        Generate the admin Router with all CRUD routes.

        Returns a Router that can be included in the app.
        """
        from eden.admin.views import (
            admin_dashboard,
            admin_delete_view,
            admin_detail_view,
            admin_list_view,
        )
        from eden.auth.decorators import roles_required

        router = Router(prefix=prefix)
        auth_guard = roles_required(["admin"])

        # Dashboard
        site = self

        @router.get("/", name="admin_dashboard")
        @auth_guard
        async def dashboard(request):
            return await admin_dashboard(request, site)

        # Register routes for each model
        for model, model_admin in self._registry.items():
            # Capture variables in a dedicated scope to avoid loop closure issues
            def register_model_routes(m, ma):
                t = m.__tablename__
                
                @router.get(f"/{t}/", name=f"admin_{t}_list")
                @auth_guard
                async def list_view(request):
                    return await admin_list_view(request, m, ma)

                @router.get(f"/{t}/{{record_id}}", name=f"admin_{t}_detail")
                @auth_guard
                async def detail_view(request, record_id: str):
                    return await admin_detail_view(request, m, ma, record_id)

                @router.post(f"/{t}/{{record_id}}/delete", name=f"admin_{t}_delete")
                @auth_guard
                async def delete_view(request, record_id: str):
                    return await admin_delete_view(request, m, ma, record_id)

            register_model_routes(model, model_admin)

        return router


# Global default admin site
admin = AdminSite()

class TabularInline:
    """
    Stub for TabularInline admin classes.
    Allows defining related models to be edited inline on the parent page.
    """
    model: type | None = None
    extra: int = 3


__all__ = [
    "admin",
    "AdminSite",
    "ModelAdmin",
    "TabularInline",
]
