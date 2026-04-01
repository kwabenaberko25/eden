"""
🌿 Eden — A batteries-included async Python web framework.

Django's features · FastAPI's speed · Flask's simplicity.

**Core Imports**: The main API surface for building web applications.

For ORM/Database features:
    from eden.db import Model, Query, Database, F, Q, ...

For Payments (requires: pip install eden-framework[payments]):
    from eden.payments import Customer, Subscription, StripeProvider

For Cloud Storage (requires: pip install eden-framework[storage]):
    from eden.storage import S3StorageBackend, LocalStorageBackend

For Background Tasks (requires: pip install eden-framework[tasks]):
    from eden.tasks import Task, broker

For Email/SMTP (requires: pip install eden-framework[mail]):
    from eden.mail import send_mail, EmailMessage

For Tenancy/Multi-tenant (built-in):
    from eden.tenancy import Tenant, TenantMiddleware, get_current_tenant

For Admin Panel (built-in):
    from eden.admin import AdminSite, ModelAdmin
"""

__version__ = "1.0.0"

# ── Always-loaded core (lightweight) ──
from eden.app import Eden, Eden as App
from eden.routing import Route, Router, WebSocketRoute, View
from eden.requests import Request
from eden.responses import (
    Response, JsonResponse, HtmlResponse, RedirectResponse,
    FileResponse, StreamingResponse, html, json, redirect,
)
from eden.dependencies import Depends
from eden.context import request, user
from eden.config import Config
from eden.logging import get_logger, setup_logging

# ── Lazy-loaded subsystems ──
_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    # Database
    "Model": ("eden.db", "Model"),
    "Database": ("eden.db", "Database"),
    "QuerySet": ("eden.db", "QuerySet"),
    "Q": ("eden.db", "Q"),
    "F": ("eden.db", "F"),
    "f": ("eden.db", "f"),
    "Page": ("eden.db", "Page"),
    "StringField": ("eden.db", "StringField"),
    "IntField": ("eden.db", "IntField"),
    "FloatField": ("eden.db", "FloatField"),
    "BoolField": ("eden.db", "BoolField"),
    "DateTimeField": ("eden.db", "DateTimeField"),
    "UUIDField": ("eden.db", "UUIDField"),
    "TextField": ("eden.db", "TextField"),
    "JSONField": ("eden.db", "JSONField"),
    "JSONBField": ("eden.db", "JSONBField"),
    "ArrayField": ("eden.db", "ArrayField"),
    "EnumField": ("eden.db", "EnumField"),
    "DecimalField": ("eden.db", "DecimalField"),
    "FileField": ("eden.db", "FileField"),
    "ForeignKeyField": ("eden.db", "ForeignKeyField"),
    "Relationship": ("eden.db", "Relationship"),
    "SoftDeleteMixin": ("eden.db", "SoftDeleteMixin"),
    "ValidatorMixin": ("eden.db", "ValidatorMixin"),
    "ValidationErrors": ("eden.db", "ValidationErrors"),
    "MigrationManager": ("eden.db", "MigrationManager"),
    "get_db": ("eden.db", "get_db"),
    "select": ("eden.db", "select"),
    "update": ("eden.db", "update"),
    "delete": ("eden.db", "delete"),
    "insert": ("eden.db", "insert"),
    "func": ("eden.db", "func"),
    "text": ("eden.db", "text"),
    "and_": ("eden.db", "and_"),
    "or_": ("eden.db", "or_"),
    "not_": ("eden.db", "not_"),
    "desc": ("eden.db", "desc"),
    "asc": ("eden.db", "asc"),
    "JSON": ("eden.db", "JSON"),
    "Mapped": ("eden.db", "Mapped"),

    # WebSocket & Realtime
    "WebSocket": ("eden.websocket", "WebSocket"),
    "WebSocketDisconnect": ("eden.websocket", "WebSocketDisconnect"),
    "WebSocketRouter": ("eden.websocket", "WebSocketRouter"),
    "ConnectionManager": ("eden.websocket", "ConnectionManager"),
    "connection_manager": ("eden.websocket", "connection_manager"),
    "realtime_manager": ("eden.websocket", "connection_manager"),

    # Error Handling
    "EdenException": ("eden.exceptions", "EdenException"),
    "HttpException": ("eden.exceptions", "HttpException"),
    "BadRequest": ("eden.exceptions", "BadRequest"),
    "Unauthorized": ("eden.exceptions", "Unauthorized"),
    "Forbidden": ("eden.exceptions", "Forbidden"),
    "NotFound": ("eden.exceptions", "NotFound"),
    "MethodNotAllowed": ("eden.exceptions", "MethodNotAllowed"),
    "Conflict": ("eden.exceptions", "Conflict"),
    "ValidationError": ("eden.exceptions", "ValidationError"),
    "TooManyRequests": ("eden.exceptions", "TooManyRequests"),
    "InternalServerError": ("eden.exceptions", "InternalServerError"),

    # Templating
    "EdenTemplates": ("eden.templating", "EdenTemplates"),
    "render_template": ("eden.templating", "render_template"),

    # Components
    "Component": ("eden.components", "Component"),
    "render_component": ("eden.components", "render_component"),
    "action": ("eden.components", "action"),

    # Forms & Validation
    "BaseForm": ("eden.forms", "BaseForm"),
    "ModelForm": ("eden.forms", "ModelForm"),
    "FormField": ("eden.forms", "FormField"),
    "Schema": ("eden.forms", "Schema"),
    "v": ("eden.forms", "v"),
    "field": ("eden.forms", "field"),
    "validate_email": ("eden.validators", "validate_email"),
    "validate_phone": ("eden.validators", "validate_phone"),
    "validate_password": ("eden.validators", "validate_password"),
    "validate_url": ("eden.validators", "validate_url"),
    "validate_slug": ("eden.validators", "validate_slug"),
    "validate_ip": ("eden.validators", "validate_ip"),
    "validate_color": ("eden.validators", "validate_color"),
    "validate_credit_card": ("eden.validators", "validate_credit_card"),
    "validate_date": ("eden.validators", "validate_date"),
    "validate_username": ("eden.validators", "validate_username"),

    # HTML Utilities
    "HtmxResponse": ("eden.htmx", "HtmxResponse"),
    "is_htmx": ("eden.htmx", "is_htmx"),

    # Services
    "Service": ("eden.services", "Service"),

    # Background Tasks
    "EdenBroker": ("eden.tasks", "EdenBroker"),
    "create_broker": ("eden.tasks", "create_broker"),

    # Email & Messaging
    "send_mail": ("eden.mail", "send_mail"),
    "EmailMessage": ("eden.mail", "EmailMessage"),
    "SMTPBackend": ("eden.mail", "SMTPBackend"),
    "success": ("eden.messages", "success"),
    "error": ("eden.messages", "error"),
    "info": ("eden.messages", "info"),
    "warning": ("eden.messages", "warning"),
    "debug": ("eden.messages", "debug"),

    # Authentication & Security
    "APIKey": ("eden.auth", "APIKey"),
    "APIKeyBackend": ("eden.auth", "APIKeyBackend"),
    "login_required": ("eden.auth", "login_required"),
    "roles_required": ("eden.auth", "roles_required"),
    "role_required": ("eden.auth", "role_required"),
    "require_permission": ("eden.auth", "require_permission"),
    "permission_required": ("eden.auth", "permission_required"),
    "permissions_required": ("eden.auth", "permissions_required"),
    "staff_required": ("eden.auth", "staff_required"),
    "check_permission": ("eden.auth", "check_permission"),
    "authenticate": ("eden.auth", "authenticate"),
    "create_user": ("eden.auth", "create_user"),
    "rate_limit": ("eden.middleware.rate_limit", "rate_limit"),

    # Tenancy
    "Tenant": ("eden.tenancy.models", "Tenant"),
    "AnonymousTenant": ("eden.tenancy.models", "AnonymousTenant"),
    "TenantMixin": ("eden.tenancy.mixins", "TenantMixin"),
    "TenantMiddleware": ("eden.tenancy.middleware", "TenantMiddleware"),
    "get_current_tenant": ("eden.tenancy.context", "get_current_tenant"),

    # Admin Panel
    "AdminSite": ("eden.admin", "AdminSite"),
    "ModelAdmin": ("eden.admin", "ModelAdmin"),
    "admin": ("eden.admin", "admin"),
    "admin_site": ("eden.admin", "admin"),

    # Testing & Client
    "TestClient": ("eden.testing", "TestClient"),

    # Migrations
    "init_migrations": ("eden.db.migrations", "init_migrations"),
    "create_migration": ("eden.db.migrations", "create_migration"),
    "apply_migrations": ("eden.db.migrations", "run_upgrade"),
    "rollback_migration": ("eden.db.migrations", "run_downgrade"),
    "show_history": ("eden.db.migrations", "show_history"),
}

def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]
        try:
            import importlib
            module = importlib.import_module(module_path)
            value = getattr(module, attr_name)
            # Cache it in the module namespace for subsequent access
            globals()[name] = value
            return value
        except Exception:
            if name == "TestClient":
                return None
            if name in (
                "init_migrations", "create_migration", "apply_migrations", 
                "rollback_migration", "show_history"
            ):
                return None
            raise
    raise AttributeError(f"module 'eden' has no attribute {name!r}")


__all__ = [
    # ── Core Application ───────────────────────────────────────────────────
    "Eden",
    "App",
    "Router",
    "Route",
    "WebSocketRoute",
    "View",
    "WebSocket",
    "WebSocketDisconnect",
    "Request",
    "Response",
    "JsonResponse",
    "HtmlResponse",
    "RedirectResponse",
    "FileResponse",
    "StreamingResponse",
    "json",
    "html",
    "redirect",
    "Depends",
    
    # ── Database & ORM (use: from eden.db import ...) ─────────────────────
    "Model",
    "Database",
    "QuerySet",
    "Q",
    "F",
    "f",
    "Page",
    "StringField",
    "IntField",
    "FloatField",
    "BoolField",
    "DateTimeField",
    "UUIDField",
    "TextField",
    "JSONField",
    "JSONBField",
    "ArrayField",
    "EnumField",
    "DecimalField",
    "FileField",
    "ForeignKeyField",
    "Relationship",
    "SoftDeleteMixin",
    "ValidatorMixin",
    "ValidationErrors",
    "MigrationManager",
    "get_db",
    "select",
    "update",
    "delete",
    "insert",
    "func",
    "text",
    "and_",
    "or_",
    "not_",
    "desc",
    "asc",
    "JSON",
    "Mapped",
    
    # ── WebSocket & Realtime ──────────────────────────────────────────────
    "WebSocketRouter",
    "ConnectionManager",
    "connection_manager",
    "realtime_manager",
    
    # ── Context ────────────────────────────────────────────────────────────
    "request",
    "user",
    
    # ── Error Handling ────────────────────────────────────────────────────
    "EdenException",
    "HttpException",
    "BadRequest",
    "Unauthorized",
    "Forbidden",
    "NotFound",
    "MethodNotAllowed",
    "Conflict",
    "ValidationError",
    "TooManyRequests",
    "InternalServerError",
    
    # ── Templating ────────────────────────────────────────────────────────
    "EdenTemplates",
    "render_template",
    
    # ── Components ────────────────────────────────────────────────────────
    "Component",
    "render_component",
    "action",
    
    # ── Forms & Validation ────────────────────────────────────────────────
    "BaseForm",
    "ModelForm",
    "FormField",
    "Schema",
    "v",
    "field",
    "validate_email",
    "validate_phone",
    "validate_password",
    "validate_url",
    "validate_slug",
    "validate_ip",
    "validate_color",
    "validate_credit_card",
    "validate_date",
    "validate_username",
    
    # ── HTML Utilities ────────────────────────────────────────────────────
    "HtmxResponse",
    "is_htmx",
    
    # ── Services ──────────────────────────────────────────────────────────
    "Service",
    
    # ── Background Tasks ──────────────────────────────────────────────────
    "EdenBroker",
    "create_broker",
    
    # ── Email & Messaging ─────────────────────────────────────────────────
    "send_mail",
    "EmailMessage",
    "SMTPBackend",
    "success",
    "error",
    "info",
    "warning",
    "debug",
    
    # ── Logging ───────────────────────────────────────────────────────────
    "get_logger",
    "setup_logging",
    
    # ── Authentication & Security ─────────────────────────────────────────
    "APIKey",
    "APIKeyBackend",
    "login_required",
    "roles_required",
    "role_required",
    "require_permission",
    "staff_required",
    "permission_required",
    "permissions_required",
    "check_permission",
    "authenticate",
    "create_user",
    "rate_limit",
    
    # ── Tenancy (Multi-tenant row-level security) ──────────────────────────
    "Tenant",
    "AnonymousTenant",
    "TenantMixin",
    "TenantMiddleware",
    "get_current_tenant",
    
    # ── Admin Panel ────────────────────────────────────────────────────────
    "AdminSite",
    "ModelAdmin",
    "admin",
    "admin_site",
    
    # ── Testing & Client ──────────────────────────────────────────────────
    "TestClient",
    
    # ── Migrations ────────────────────────────────────────────────────────
    "init_migrations",
    "create_migration",
    "apply_migrations",
    "rollback_migration",
    "show_history",
    
    # ── Configuration ─────────────────────────────────────────────────────
    "Config",
]
