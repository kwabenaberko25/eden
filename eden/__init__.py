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

__version__ = "0.1.0"

# ── Core Application ──────────────────────────────────────────────────────
from eden.app import Eden, Eden as App
from eden.routing import Route, Router, WebSocketRoute, View
from eden.requests import Request
from eden.responses import (
    Response,
    JsonResponse,
    HtmlResponse,
    RedirectResponse,
    FileResponse,
    StreamingResponse,
    html,
    json,
    redirect,
)
from eden.dependencies import Depends

# ── Database & ORM (from eden.db package) ────────────────────────────────
# Recommended: from eden.db import Model, QuerySet, Database, etc.
# These are available here for backward compatibility:
from eden.db import (
    Model,
    Database,
    QuerySet,
    Q,
    F,
    f,
    Page,
    StringField,
    IntField,
    FloatField,
    BoolField,
    DateTimeField,
    UUIDField,
    TextField,
    JSONField,
    JSONBField,
    ArrayField,
    EnumField,
    DecimalField,
    FileField,
    ForeignKeyField,
    Relationship,
    SoftDeleteMixin,
    ValidatorMixin,
    ValidationErrors,
    MigrationManager,
    get_db,
    # SQLAlchemy utilities
    select,
    update,
    delete,
    insert,
    func,
    text,
    and_,
    or_,
    not_,
    desc,
    asc,
    JSON,
)

# ── WebSocket & Realtime ──────────────────────────────────────────────────
from eden.websocket import (
    WebSocket, 
    WebSocketDisconnect, 
    WebSocketRouter, 
    ConnectionManager,
    connection_manager
)
realtime_manager = connection_manager

# ── Routing & Context ─────────────────────────────────────────────────────
from eden.context import request, user

# ── Error Handling ────────────────────────────────────────────────────────
from eden.exceptions import (
    BadRequest,
    Conflict,
    EdenException,
    Forbidden,
    HttpException,
    InternalServerError,
    MethodNotAllowed,
    NotFound,
    TooManyRequests,
    Unauthorized,
    ValidationError,
)

# ── Templating ────────────────────────────────────────────────────────────
from eden.templating import EdenTemplates, render_template

# ── Components ────────────────────────────────────────────────────────────
from eden.components import Component, render_component, action

# ── Forms & Validation ────────────────────────────────────────────────────
from eden.forms import BaseForm, ModelForm, FormField, Schema, v, field
from eden.validators import (
    validate_email,
    validate_phone,
    validate_password,
    validate_url,
    validate_slug,
    validate_ip,
    validate_color,
    validate_credit_card,
    validate_date,
    validate_username,
)

# ── HTML Utilities ────────────────────────────────────────────────────────
from eden.htmx import HtmxResponse, is_htmx

# ── Services (Business Logic) ─────────────────────────────────────────────
from eden.services import Service

# ── Logging ───────────────────────────────────────────────────────────────
from eden.logging import get_logger, setup_logging

# ── Authentication (API Keys, Decorators) ────────────────────────────────
# Note: Advanced auth features (OAuth, SAML) may require additional extras
from eden.auth import (
    APIKey,
    APIKeyBackend,
    login_required,
    roles_required,
    require_permission,
    staff_required,
    check_permission,
    authenticate,
    create_user,
)
from eden.auth.complete import permission_required
from eden.middleware.rate_limit import rate_limit

# ── Tenancy (Multi-tenant row-level security, built-in) ───────────────────
from eden.tenancy.models import Tenant, AnonymousTenant
from eden.tenancy.mixins import TenantMixin
from eden.tenancy.middleware import TenantMiddleware
from eden.tenancy.context import get_current_tenant

# ── Admin (Built-in admin panel) ──────────────────────────────────────────
from eden.admin import AdminSite, ModelAdmin, admin
admin_site = admin

# ── Testing & Client ──────────────────────────────────────────────────────
try:
    from eden.testing import TestClient
except ImportError:
    # pytest not installed; provide stub
    TestClient = None

# ── Migrations ────────────────────────────────────────────────────────────
try:
    from eden.db.migrations import (
        init_migrations,
        create_migration,
        run_upgrade as apply_migrations,
        run_downgrade as rollback_migration,
        show_history
    )
except ImportError:
    init_migrations = None
    create_migration = None
    apply_migrations = None
    rollback_migration = None
    show_history = None

# ── Configuration ─────────────────────────────────────────────────────────
from eden.config import Config

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
    
    # ── Logging ───────────────────────────────────────────────────────────
    "get_logger",
    "setup_logging",
    
    # ── Authentication & Security ─────────────────────────────────────────
    "APIKey",
    "APIKeyBackend",
    "login_required",
    "roles_required",
    "require_permission",
    "staff_required",
    "permission_required",
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
