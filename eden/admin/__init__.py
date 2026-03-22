"""
Eden — Admin Panel

Auto-generated admin interface for managing Model data.
"""

from typing import Any, Optional, Callable, Type

from eden.admin.options import ModelAdmin, TabularInline, StackedInline
from eden.routing import Router
from eden.responses import JsonResponse, Response
from eden.requests import Request

# Re-export new widget system for backward compatibility
try:
    from eden.admin.widgets import (
        FieldWidget,
        TextField,
        EmailField,
        PasswordField,
        TextAreaField,
        SelectField,
        CheckboxField,
        DateTimeField,
        ImageField,
        Action,
        DeleteAction,
        DeactivateAction,
        ExportAction,
        ApproveAction,
        AuditEntry,
        AuditTrail,
        AdminPanel,
        AdminRegistry,
        register_admin,
        get_admin,
    )
except ImportError:
    # Graceful fallback if widgets module not available
    pass


class AdminSite:
    """
    Registry for admin-registered models.

    Generates CRUD views and a dashboard for all registered models.

    Usage:
        from eden.responses import HtmlResponse, RedirectResponse, JsonResponse

        class UserAdmin(ModelAdmin):
            list_display = ["email", "full_name", "is_active"]
            search_fields = ["email", "full_name"]

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

    def register_defaults(self):
        """Register core models (User, AuditLog, etc.) if they are available."""
        from eden.admin.options import ModelAdmin
        
        try:
            from eden.auth.models import User
            if not self.is_registered(User):
                class UserAdmin(ModelAdmin):
                    list_display = ["email", "full_name", "is_active", "is_superuser"]
                    search_fields = ["email", "full_name"]
                    list_filter = ["is_active", "is_staff", "is_superuser"]
                self.register(User, UserAdmin)
        except ImportError:
            pass

        try:
            from eden.admin.models import AuditLog
            if not self.is_registered(AuditLog):
                class AuditLogAdmin(ModelAdmin):
                    list_display = ["timestamp", "user_id", "action", "model_name", "record_id"]
                    list_filter = ["action", "model_name"]
                    readonly_fields = ["id", "timestamp", "user_id", "action", "model_name", "record_id", "changes"]
                self.register(AuditLog, AuditLogAdmin)
        except ImportError:
            pass

        try:
            from eden.auth.api_key_model import APIKey
            if not self.is_registered(APIKey):
                class APIKeyAdmin(ModelAdmin):
                    list_display = ["name", "prefix", "user_id", "created_at", "revoked_at"]
                    search_fields = ["name", "prefix"]
                    list_filter = ["revoked_at"]
                self.register(APIKey, APIKeyAdmin)
        except ImportError:
            pass

    def build_router(self, prefix: str = "/admin") -> Router:
        """
        Generate the admin Router with all CRUD routes.

        Returns a Router that can be included in the app.
        """
        # Auto-register core models if not already registered
        self.register_defaults()

        from eden.admin.views import (
            admin_add_view,
            admin_dashboard,
            admin_delete_view,
            admin_detail_view,
            admin_edit_view,
            admin_list_view,
            admin_login,
        )
        import functools
        from eden.responses import RedirectResponse

        router = Router(prefix=prefix)
        
        def admin_required(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper(request, *args, **kwargs):
                user = getattr(request.state, "user", None)
                if not user:
                    from eden.auth.base import get_current_user
                    user = await get_current_user(request)
                
                # Fallback: manually check session if auth middleware didn't run or hasn't populated state
                if not user and hasattr(request, "session"):
                    from eden.auth.backends.session import SessionBackend
                    backend = SessionBackend()
                    user = await backend.authenticate(request)
                    if user:
                        request.state.user = user
                
                if not user:
                    return RedirectResponse(url=f"{prefix}/login?next={request.url.path}")
                
                if not getattr(user, "is_staff", False) and not getattr(user, "is_superuser", False):
                    from eden.exceptions import Forbidden
                    raise Forbidden(detail="Staff access required.")
                
                return await func(request, *args, **kwargs)
            return wrapper

        # Login
        site = self
        @router.route("/login", methods=["GET", "POST"], name="admin_login")
        async def login_view(request):
            return await admin_login(request, site)

        # Dashboard

        @router.get("/", name="admin_dashboard")
        @admin_required
        async def dashboard(request):
            return await admin_dashboard(request, site)

        # Register routes for each model
        for model, model_admin in self._registry.items():
            # Capture variables in a dedicated scope to avoid loop closure issues
            def register_model_routes(m: Any, ma: ModelAdmin) -> None:
                t = m.__tablename__
                
                @router.get(f"/{t}/", name=f"admin_{t}_list")
                @admin_required
                async def list_view(request: Request) -> Response:
                    return await admin_list_view(request, m, ma)

                @router.route(f"/{t}/add", methods=["GET", "POST"], name=f"admin_{t}_add")
                @admin_required
                async def add_view(request: Request) -> Response:
                    return await admin_add_view(request, m, ma)

                @router.get(f"/{t}/{{record_id}}", name=f"admin_{t}_detail")
                @admin_required
                async def detail_view(request: Request, record_id: str) -> Response:
                    return await admin_detail_view(request, m, ma, record_id)

                @router.route(f"/{t}/{{record_id}}/edit", methods=["GET", "POST"], name=f"admin_{t}_edit")
                @admin_required
                async def edit_view(request: Request, record_id: str) -> Response:
                    return await admin_edit_view(request, m, ma, record_id)

                @router.post(f"/{t}/action", name=f"admin_{t}_action")
                @admin_required
                async def action_view(request: Request) -> JsonResponse:
                    # For bulk actions
                    data = await request.json()
                    action_name = data.get("action")
                    selected_ids = data.get("ids", [])
                    
                    # Find action in model_admin.actions
                    for action_class in ma.actions:
                        action = action_class()
                        if action.name == action_name:
                            result = await action.execute(selected_ids, model=m)
                            return JsonResponse(result)
                    
                    return JsonResponse({"message": f"Action {action_name} not found"}, status_code=404)

                @router.post(f"/{t}/{{record_id}}/delete", name=f"admin_{t}_delete")
                @admin_required
                async def delete_view(request: Request, record_id: str) -> Response:
                    return await admin_delete_view(request, m, ma, record_id)

            register_model_routes(model, model_admin)

        return router



# Global default admin site
admin = AdminSite()

# Inlines are now fully implemented in options.py


__all__ = [
    # Legacy admin interface
    "admin",
    "AdminSite",
    "ModelAdmin",
    "TabularInline",
    "StackedInline",
    # New widget system
    "FieldWidget",
    "TextField",
    "EmailField",
    "PasswordField",
    "TextAreaField",
    "SelectField",
    "CheckboxField",
    "DateTimeField",
    "ImageField",
    # Actions
    "Action",
    "DeleteAction",
    "DeactivateAction",
    "ExportAction",
    "ApproveAction",
    # Audit
    "AuditEntry",
    "AuditTrail",
    # Admin configurations
    "AdminPanel",
    "AdminRegistry",
    "register_admin",
    "get_admin",
]
