from datetime import datetime
from typing import Any
from eden.db import (
    Model, StringField, TextField, DateTimeField, JSONField, UUIDField, 
    BoolField, ForeignKeyField, AllowPublic, AllowAuthenticated, AllowRoles
)
import uuid

class AuditLog(Model):
    """
    Tracks changes made to models via the admin panel or ORM hooks.
    """
    __tablename__ = "eden_audit_logs"
    __rbac__ = {
        "read": AllowPublic(),
        "create": AllowPublic()
    }

    id: uuid.UUID = UUIDField(primary_key=True, default_factory=uuid.uuid4)
    tenant_id: str | None = StringField(nullable=True, max_length=255) # For RLS/isolation
    user_id: str | None = StringField(nullable=True, max_length=255) # ID of user who made the change
    correlation_id: str | None = StringField(nullable=True, max_length=255) # Request ID for tracing
    action: str = StringField(max_length=50) # 'create', 'update', 'delete', 'action'
    model_name: str = StringField(max_length=255)
    record_id: str = StringField(max_length=255)
    changes: dict | None = JSONField(nullable=True) # Dict of old/new values
    timestamp: datetime = DateTimeField(auto_now_add=True)

    @classmethod
    async def log(cls, user_id: str | None, action: str, model: Any, record_id: str, changes: dict | None = None, correlation_id: str | None = None) -> None:
        from eden.context import get_tenant_id, get_request_id
        await cls.create(
            tenant_id=get_tenant_id(),
            user_id=user_id,
            correlation_id=correlation_id or get_request_id(),
            action=action,
            model_name=model.__name__ if hasattr(model, "__name__") else str(model),
            record_id=str(record_id),
            changes=changes
        )

class SupportTicket(Model):
    """
    A support request from a user or tenant.
    """
    __tablename__ = "eden_support_tickets"
    __rbac__ = {
        "read": AllowAuthenticated(),
        "create": AllowAuthenticated(),
        "update": AllowRoles(["admin", "support"])
    }

    id: uuid.UUID = UUIDField(primary_key=True, default_factory=uuid.uuid4)
    tenant_id: str | None = StringField(nullable=True, max_length=255)
    user_id: str = StringField(max_length=255)
    subject: str = StringField(max_length=255)
    status: str = StringField(max_length=20, default="open") # open, pending, resolved, closed
    priority: str = StringField(max_length=20, default="medium") # low, medium, high, urgent
    created_at: datetime = DateTimeField(auto_now_add=True)
    updated_at: datetime = DateTimeField(auto_now=True)

class TicketMessage(Model):
    """
    A single message or reply within a support ticket.
    """
    __tablename__ = "eden_ticket_messages"
    __rbac__ = {
        "read": AllowAuthenticated(),
        "create": AllowAuthenticated()
    }

    id: uuid.UUID = UUIDField(primary_key=True, default_factory=uuid.uuid4)
    ticket_id: uuid.UUID = ForeignKeyField("eden_support_tickets.id")
    user_id: str = StringField(max_length=255)
    body: str = TextField()
    is_admin: bool = BoolField(default=False)
    created_at: datetime = DateTimeField(auto_now_add=True)

class AdminConfig(Model):
    """
    Stores dynamic UI configurations for models (e.g., column visibility, filters).
    """
    __tablename__ = "eden_admin_configs"
    __rbac__ = {
        "read": AllowPublic(),
        "update": AllowRoles(["admin"])
    }

    id: uuid.UUID = UUIDField(primary_key=True, default_factory=uuid.uuid4)
    model_name: str = StringField(max_length=255, unique=True)
    config: dict = JSONField(default={}) # e.g., {"list_display": ["id", "name"], "search_fields": ["name"]}
    updated_at: datetime = DateTimeField(auto_now=True)


class PasswordHistory(Model):
    """
    Tracks password change history for admin users to prevent reuse.
    """
    __tablename__ = "eden_password_history"
    __rbac__ = {
        "read": AllowRoles(["admin"]),
        "create": AllowRoles(["admin"])
    }

    id: uuid.UUID = UUIDField(primary_key=True, default_factory=uuid.uuid4)
    username: str = StringField(max_length=255)  # Reference to admin user
    password_hash: str = TextField()  # Argon2 hash
    changed_at: datetime = DateTimeField(auto_now_add=True)


class PasswordResetToken(Model):
    """
    Tracks password reset tokens for admin users.
    """
    __tablename__ = "eden_password_reset_tokens"
    __rbac__ = {
        "read": AllowRoles(["admin"]),
        "create": AllowRoles(["admin"])
    }

    id: uuid.UUID = UUIDField(primary_key=True, default_factory=uuid.uuid4)
    username: str = StringField(max_length=255)  # Reference to admin user
    token: str = StringField(max_length=255, unique=True)  # URL-safe token
    created_at: datetime = DateTimeField(auto_now_add=True)
    expires_at: datetime = DateTimeField()  # Expiry time
    used: bool = BoolField(default=False)  # Whether token was used


class EmailVerificationToken(Model):
    """
    Tracks email verification tokens for new admin users.
    """
    __tablename__ = "eden_email_verification_tokens"
    __rbac__ = {
        "read": AllowRoles(["admin"]),
        "create": AllowRoles(["admin"])
    }

    id: uuid.UUID = UUIDField(primary_key=True, default_factory=uuid.uuid4)
    username: str = StringField(max_length=255)  # Reference to admin user
    email: str = StringField(max_length=255)  # Email to verify
    token: str = StringField(max_length=255, unique=True)  # URL-safe token
    created_at: datetime = DateTimeField(auto_now_add=True)
    expires_at: datetime = DateTimeField()  # Expiry time
    verified: bool = BoolField(default=False)  # Whether email was verified


class TOTPSecret(Model):
    """
    Stores TOTP secrets for admin users with 2FA enabled.
    """
    __tablename__ = "eden_totp_secrets"
    __rbac__ = {
        "read": AllowRoles(["admin"]),
        "create": AllowRoles(["admin"]),
        "update": AllowRoles(["admin"])
    }

    id: uuid.UUID = UUIDField(primary_key=True, default_factory=uuid.uuid4)
    username: str = StringField(max_length=255, unique=True)  # Reference to admin user
    secret: str = TextField()  # Base32-encoded secret
    enabled_at: datetime = DateTimeField()  # When 2FA was enabled
    verified: bool = BoolField(default=False)  # Whether 2FA is verified


class BackupCode(Model):
    """
    Backup codes for account recovery when TOTP device is unavailable.
    """
    __tablename__ = "eden_backup_codes"
    __rbac__ = {
        "read": AllowRoles(["admin"]),
        "create": AllowRoles(["admin"]),
        "update": AllowRoles(["admin"])
    }

    id: uuid.UUID = UUIDField(primary_key=True, default_factory=uuid.uuid4)
    username: str = StringField(max_length=255)  # Reference to admin user
    code: str = StringField(max_length=50)  # Formatted code (e.g., XXXX-XXXX)
    used: bool = BoolField(default=False)  # Whether code has been used
    used_at: datetime = DateTimeField(nullable=True)  # When code was used
