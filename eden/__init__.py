"""
🌿 Eden — A batteries-included async Python web framework.

Django's features · FastAPI's speed · Flask's simplicity.
"""

__version__ = "0.1.0"

from eden.admin import AdminSite, ModelAdmin, admin
admin_site = admin
from eden.app import Eden
from eden.auth.api_key_model import APIKey
from eden.auth.backends.api_key import APIKeyBackend
from eden.auth.decorators import login_required, roles_required, require_permission
from eden.db import (
    BoolField,
    Database,
    DateTimeField,
    Model,
    F,
    f,
    FloatField,
    IntField,
    Page,
    Q,
    QuerySet,
    SoftDeleteMixin,
    StringField,
    TextField,
    UUIDField,
    FileField,
    get_db,
)
from eden.services import Service
from eden.db.fields import ForeignKeyField, Relationship
from eden.db.fields import ForeignKeyField, Relationship
from eden.forms import BaseForm
from eden.htmx import HtmxResponse, is_htmx
from eden.dependencies import Depends
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
from eden.logging import get_logger, setup_logging
from eden.mail import EmailMessage, configure_mail, send_mail
from eden.payments import Customer, CustomerMixin, Subscription, WebhookRouter
from eden.requests import Request
from eden.responses import (
    StreamingResponse,
    html,
    json,
    redirect,
)
from eden.cache import cache_view
from eden.templating import EdenTemplates, render_template
from eden.components import Component, render_component
from eden.payments.providers import StripeProvider
from eden.resources import Resource, TenantResource, action
from eden.routing import Route, Router, WebSocketRoute
from eden.websocket import WebSocket, WebSocketDisconnect, WebSocketRouter, ConnectionManager
from eden.context import request, user
from eden.storage import LocalStorageBackend, StorageBackend, StorageManager, storage
from eden.storage_backends import S3StorageBackend, SupabaseStorageBackend
from eden.tenancy.middleware import TenantMiddleware
from eden.tenancy.models import AnonymousTenant, Tenant
from eden.tenancy.context import get_current_tenant
from eden.tenancy.mixins import TenantMixin
from eden.db.access import AccessControl, PermissionRule
from eden.db.migrations import MigrationManager
from eden.validators import (
    EdenColor,
    EdenEmail,
    EdenPhone,
    EdenSlug,
    EdenURL,
    ValidationResult,
    validate_color,
    validate_credit_card,
    validate_date,
    validate_email,
    validate_file_type,
    validate_gps,
    validate_iban,
    validate_ip,
    validate_national_id,
    validate_password,
    validate_phone,
    validate_postcode,
    validate_range,
    validate_slug,
    validate_url,
    validate_username,
)

__all__ = [
    # Core
    "Eden",
    "Router",
    "Route",
    "WebSocketRoute",
    "WebSocket",
    "WebSocketDisconnect",
    "Request",
    "Depends",
    # Database / ORM
    "Model",
    "Resource",
    "TenantResource",
    "action",
    "AccessControl",
    "PermissionRule",
    "MigrationManager",
    "f",
    "Database",
    "get_db",
    "Q",
    "F",
    "Page",
    "SoftDeleteMixin",
    "StringField",
    "IntField",
    "TextField",
    "BoolField",
    "FloatField",
    "DateTimeField",
    "UUIDField",
    "ForeignKeyField",
    "Relationship",
    "QuerySet",
    # Responses
    "Response",
    "JsonResponse",
    "HtmlResponse",
    "RedirectResponse",
    "FileResponse",
    "StreamingResponse",
    "FileField",
    "Service",
    # Response shortcuts
    "json",
    "html",
    "redirect",
    "render_template",
    # Exceptions
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
    # Logging
    "setup_logging",
    "get_logger",
    # Auth — API Keys
    "APIKey",
    "APIKeyBackend",
    # Tenancy
    "Tenant",
    "AnonymousTenant",
    "TenantMixin",
    "TenantMiddleware",
    # Mail
    "send_mail",
    "EmailMessage",
    "configure_mail",
    # Admin
    "admin",
    "AdminSite",
    "admin_site",
    "ModelAdmin",
    # Payments
    "Customer",
    "Subscription",
    "CustomerMixin",
    "WebhookRouter",
    # Storage
    "storage",
    "StorageBackend",
    "LocalStorageBackend",
    "S3StorageBackend",
    "SupabaseStorageBackend",
    "request",
    "user",
    "BaseForm",
    "HtmxResponse",
    "is_htmx",
    "login_required",
    "roles_required",
    "require_permission",
    "get_current_tenant",
    "WebSocketRouter",
    "ConnectionManager",
    "render_component",
    "StorageManager",
    "StripeProvider",
    "cache_view",
]
