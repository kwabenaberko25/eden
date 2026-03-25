"""
Eden — Admin Panel

Auto-generated admin interface for managing Model data.
"""

from typing import Any, Optional, Callable, Type, List, Dict, Iterable

import os
from .options import ModelAdmin, TabularInline, StackedInline
from eden.routing import Router
from eden.responses import JsonResponse, Response, HtmlResponse
from eden.requests import Request
from eden.templating import EdenTemplates
from .theme import default_theme
from eden.db import Model, _MISSING

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
        StatWidget,
        ChartWidget,
        DashboardWidget,
        register_dashboard,
        get_dashboard,
        display,
    )
except ImportError:
    # Graceful fallback if widgets module not available
    def display(description: str | None = None, boolean: bool | None = None) -> Callable:
        def decorator(func: Callable) -> Callable:
            if description:
                setattr(func, "short_description", description)
            if boolean is not None:
                setattr(func, "boolean", boolean)
            return func
        return decorator
    pass


class AdminSite:
    """
    Registry for admin-registered models.

    Generates CRUD views and a dashboard for all registered models.
    """

    def __init__(self, theme=None):
        self._registry: dict[type, ModelAdmin] = {}
        self.theme = theme or default_theme
        
        # Initialize the modern template engine for the admin panel
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        self.templates = EdenTemplates(directory=template_dir)
        
        # Register global variables for the admin panel
        self.templates.env.globals.update({
            "admin_site": self,
            "theme": self.theme,
            "registry": self._get_template_registry(),
        })

        # Provide easy access to widgets for ModelAdmin configuration
        try:
            import eden.admin.widgets as widgets
            self.widgets = widgets
        except ImportError:
            self.widgets = None

    def _get_template_registry(self) -> dict[str, dict]:
        """Returns a dict of models mapping to their UI configuration for sidebar/navigation."""
        # This is a bit recursive because we want to call it when models are added
        # But for now we'll return a dynamic accessor or just re-calculate when needed
        return {} # Placeholder, will be used in build_router

    def register(self, model_or_iterable: Any, admin_class: Optional[Type] = None) -> Any:
        """
        Register a model for the admin panel.

        Can be used as a decorator or called directly:

            # As decorator (Eden auto style)
            @admin.register
            class User(Model):
                ...

            # Direct call
            admin.register(User, UserAdmin)
            admin.register([User, Profile], DefaultAdmin)
        """
        from eden.admin.options import ModelAdmin as BaseAdmin

        def _do_register(model, admin_cls=None):
            if admin_cls is None:
                # Use default ModelAdmin or the one defined on the model
                admin_cls = getattr(model, "Admin", BaseAdmin)
            
            # Instantiate correctly
            # Note: in this framework ModelAdmin constructor is assumed to be generic
            self._registry[model] = admin_cls()
            
            # Propagate to global site if this isn't the global site instance
            # (only if admin is already defined at this point)
            try:
                # 'admin' is the global instance defined at the bottom of this file
                # If we're currently executing the part that defines 'admin', it might be None
                global_site = globals().get("admin")
                if global_site and self is not global_site and model not in global_site._registry:
                    global_site.register(model, admin_cls)
            except Exception:
                pass

        # 1. Direct call with specified admin class
        if admin_class is not None:
            if isinstance(model_or_iterable, (list, tuple, set, Iterable)) and not isinstance(model_or_iterable, type):
                for m in model_or_iterable:
                    _do_register(m, admin_class)
            else:
                _do_register(model_or_iterable, admin_class)
            return admin_class

        # 2. Iterable of models (no admin class provided)
        if isinstance(model_or_iterable, (list, tuple, set, Iterable)) and not isinstance(model_or_iterable, type):
            for m in model_or_iterable:
                _do_register(m)
            return

        # 3. Decorator or Single Model Registration
        model = model_or_iterable
        
        # Determine if it's an admin class decorator: @register class MyAdmin(ModelAdmin)
        try:
            is_admin = isinstance(model, type) and issubclass(model, BaseAdmin)
        except:
            is_admin = False
            
        if is_admin:
            from_model = getattr(model, "model", None)
            if from_model:
                _do_register(from_model, model)
            return model
            
        # Decorating a model (common in tests) or direct registration
        _do_register(model)
        return model

    def dashboard(self, dashboard_class: Type) -> Type:
        """Decorator to register a dashboard class."""
        from eden.admin.widgets import register_dashboard
        register_dashboard(dashboard_class)
        return dashboard_class

    def display(self, description: str | None = None, boolean: bool | None = None) -> Callable:
        """Access the display decorator via the admin instance."""
        return display(description, boolean)

    @property
    def TabularInline(self):
        from eden.admin.options import TabularInline as TI
        return TI

    @property
    def StackedInline(self):
        from eden.admin.options import StackedInline as SI
        return SI

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
            from eden.auth.models import User, Role, Permission
            if not self.is_registered(User):
                class UserAdmin(ModelAdmin):
                    list_display = ["email", "full_name", "is_active", "is_superuser"]
                    search_fields = ["email", "full_name"]
                    list_filter = ["is_active", "is_staff", "is_superuser"]
                self.register(User, UserAdmin)
            
            if not self.is_registered(Permission):
                class PermissionAdmin(ModelAdmin):
                    list_display = ["name", "description"]
                    search_fields = ["name"]
                self.register(Permission, PermissionAdmin)
                
            if not self.is_registered(Role):
                class RoleAdmin(ModelAdmin):
                    list_display = ["name", "description"]
                    search_fields = ["name"]
                self.register(Role, RoleAdmin)
        except ImportError:
            pass

        try:
            from eden.admin.models import AuditLog, SupportTicket, TicketMessage, AdminConfig
            if not self.is_registered(AuditLog):
                class AuditLogAdmin(ModelAdmin):
                    list_display = ["timestamp", "user_id", "action", "model_name", "record_id"]
                    list_filter = ["action", "model_name"]
                    readonly_fields = ["id", "timestamp", "user_id", "action", "model_name", "record_id", "changes"]
                self.register(AuditLog, AuditLogAdmin)

            if not self.is_registered(SupportTicket):
                from eden.admin.models import TicketMessage
                class TicketMessageInline(self.TabularInline):
                    model = TicketMessage
                    extra = 1

                class SupportTicketAdmin(ModelAdmin):
                    list_display = ["subject", "user_id", "status", "priority", "created_at"]
                    list_filter = ["status", "priority"]
                    search_fields = ["subject", "user_id"]
                    readonly_fields = ["created_at", "updated_at"]
                    inlines = [TicketMessageInline]
                    icon = "fa-solid fa-headset"
                self.register(SupportTicket, SupportTicketAdmin)

            if not self.is_registered(AdminConfig):
                class AdminConfigAdmin(ModelAdmin):
                    list_display = ["model_name", "updated_at"]
                    search_fields = ["model_name"]
                    readonly_fields = ["updated_at"]
                    icon = "fa-solid fa-sliders"
                self.register(AdminConfig, AdminConfigAdmin)
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
        """
        self.register_defaults()

        # Update registry in global template context before building routes
        registry_data = {}
        for model, model_admin in self._registry.items():
            table_name = str(getattr(model, "__tablename__", model.__name__.lower()))
            registry_data[table_name] = {
                "slug": model_admin.get_slug(model),
                "icon": model_admin.icon,
                "label": model_admin.get_verbose_name(model),
                "label_plural": model_admin.get_verbose_name_plural(model),
                "table": table_name,
            }
        self.templates.env.globals["registry"] = registry_data

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

        site_instance = self
        @router.route("/login", methods=["GET", "POST"], name="admin_login")
        async def login_view(request):
            return await admin_login(request, site_instance)

        @router.get("/", name="admin_dashboard")
        @admin_required
        async def dashboard(request):
            return await admin_dashboard(request, site_instance)

        for model, model_admin in self._registry.items():
            def register_model_routes(m: Any, ma: ModelAdmin) -> None:
                t = m.__tablename__
                
                @router.get(f"/{t}/", name=f"admin_{t}_list")
                @admin_required
                async def list_view(request: Request) -> Response:
                    return await admin_list_view(request, m, ma, site_instance)

                @router.route(f"/{t}/add", methods=["GET", "POST"], name=f"admin_{t}_add")
                @admin_required
                async def add_view(request: Request) -> Response:
                    return await admin_add_view(request, m, ma, site_instance)

                @router.get(f"/{t}/{{record_id}}", name=f"admin_{t}_detail")
                @admin_required
                async def detail_view(request: Request, record_id: str) -> Response:
                    return await admin_detail_view(request, m, ma, record_id, site_instance)

                @router.route(f"/{t}/{{record_id}}/edit", methods=["GET", "POST"], name=f"admin_{t}_edit")
                @admin_required
                async def edit_view(request: Request, record_id: str) -> Response:
                    return await admin_edit_view(request, m, ma, record_id, site_instance)

                @router.post(f"/{t}/action", name=f"admin_{t}_action")
                @admin_required
                async def action_view(request: Request) -> JsonResponse:
                    data = await request.json()
                    action_name = data.get("action")
                    selected_ids = data.get("ids", [])
                    
                    for action_class in ma.actions:
                        action = action_class()
                        if action.name == action_name:
                            result = await action.execute(selected_ids, model=m)
                            return JsonResponse(result)
                    
                    return JsonResponse({"message": f"Action {action_name} not found"}, status_code=404)

                @router.post(f"/{t}/{{record_id}}/delete", name=f"admin_{t}_delete")
                @admin_required
                async def delete_view(request: Request, record_id: str) -> Response:
                    return await admin_delete_view(request, m, ma, record_id, site_instance)

            register_model_routes(model, model_admin)

        return router


# Global default admin site
admin = AdminSite()


__all__ = [
    "admin", "AdminSite", "ModelAdmin", "TabularInline", "StackedInline",
    "FieldWidget", "TextField", "EmailField", "PasswordField", "TextAreaField",
    "SelectField", "CheckboxField", "DateTimeField", "ImageField",
    "Action", "DeleteAction", "DeactivateAction", "ExportAction", "ApproveAction",
    "AuditEntry", "AuditLog", "AuditTrail", "AdminPanel", "AdminRegistry",
    "register_admin", "get_admin", "StatWidget", "ChartWidget", "DashboardWidget",
    "register_dashboard", "display"
]
