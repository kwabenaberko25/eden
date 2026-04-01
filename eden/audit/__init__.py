"""
Eden Audit System — Observability and Compliance

This module provides tools for tracking data changes and system events.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Type

from sqlalchemy import event, inspect
from sqlalchemy.orm import attributes
from sqlalchemy import JSON

from eden.admin.models import AuditLog
from eden.context import get_user, get_tenant_id, set_tenant

logger = logging.getLogger("eden.audit")

# Fields that should never be logged in plaintext
SENSITIVE_FIELDS = {
    "password", "secret", "token", "key", "api_key", "access_token", "refresh_token",
    "stripe_api_key", "webhook_secret", "client_secret", "private_key", "auth_token",
    "ssn", "cvv", "credit_card", "card_number", "passport", "social_security",
    "pin", "passphrase", "signature", "private", "salt", "hash"
}

def mask_sensitive_data(data: Any) -> Any:
    """
    Recursively remove or mask sensitive information from the audit log data.
    """
    if isinstance(data, dict):
        masked = {}
        for key, val in data.items():
            # Check if this key itself is sensitive
            is_sensitive = any(s in key.lower() for s in SENSITIVE_FIELDS)
            
            if is_sensitive:
                if isinstance(val, dict):
                    # For old/new value pairs, mask each
                    masked[key] = {
                        k: ("[REDACTED]" if v else v) for k, v in val.items()
                    }
                else:
                    masked[key] = "[REDACTED]" if val else None
            else:
                # Recurse into nested structures
                masked[key] = mask_sensitive_data(val)
        return masked
    elif isinstance(data, list):
        return [mask_sensitive_data(item) for item in data]
    return data

class AuditableMixin:
    """
    Mixin to enable automatic auditing on a Model.
    
    Uses SQLAlchemy events to capture changes even if `Model.save()` is not 
    called manually. Captures fine-grained field changes (new vs old values).
    
    Usage:
        class Project(AuditableMixin, Model):
            name: Mapped[str] = f()
    """

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Register listeners specifically for this class
        @event.listens_for(cls, 'after_insert')
        def after_insert(mapper, connection, target):
            _trigger_audit(target, "create")

        @event.listens_for(cls, 'after_update')
        def after_update(mapper, connection, target):
             _trigger_audit(target, "update")

        @event.listens_for(cls, 'after_delete')
        def after_delete(mapper, connection, target):
            _trigger_audit(target, "delete")

def _trigger_audit(target: Any, action: str):
    """
    Sync listener that triggers the async audit logging.
    Captures changes from the instance state before they are cleared.
    """
    changes = {}
    model_name = target.__class__.__name__
    record_id = str(getattr(target, "id", "N/A"))
    
    if action == "update":
        insp = inspect(target)
        # 🛡️ Fix: Use column_attrs to avoid triggering lazy-loads of relationships
        for attr in insp.mapper.column_attrs:
            history = attributes.get_history(target, attr.key)
            if history.has_changes():
                changes[attr.key] = {
                    "old": _make_json_safe(history.deleted[0]) if history.deleted else None,
                    "new": _make_json_safe(history.added[0]) if history.added else None
                }
    elif action == "create":
        # Log all non-empty fields for new records
        for column in target.__table__.columns:
            val = getattr(target, column.key, None)
            if val is not None:
                changes[column.key] = {"old": None, "new": _make_json_safe(val)}

    # Capture context for background task
    from eden.context import get_user, get_tenant_id, get_request_id
    user = get_user()
    user_id = str(getattr(user, "id", user)) if user else None
    tenant_id = get_tenant_id()
    correlation_id = get_request_id()

    # Trigger background task for logging
    try:
        from eden.context import get_app
        app = get_app()
        
        async def _do_log():
            from eden.db.session import reset_session
            from eden.context import set_tenant, set_request_id
            
            # 1. Mask sensitive changes in the background to avoid blocking the flush event
            masked_changes = mask_sensitive_data(changes)
            
            # 2. Clear session context in the background task
            reset_session() 
            
            # 3. Restore tenant and correlation context
            if tenant_id:
                set_tenant(tenant_id)
            if correlation_id:
                set_request_id(correlation_id)
                
            try:
                await AuditLog.log(
                    user_id=user_id,
                    action=action,
                    model=target.__class__,
                    record_id=record_id,
                    changes=masked_changes,
                    correlation_id=correlation_id
                )
            except Exception as exc:
                logger.warning(f"Background audit log failed: {exc}")

        # Use tracked background tasks if the app is available for graceful shutdown
        if app and hasattr(app, "spawn_background_task"):
            app.spawn_background_task(_do_log())
        else:
            # Fallback to unmanaged task if app context is missing (e.g. CLI/Scripts)
            try:
                loop = asyncio.get_running_loop()
                if loop.is_running():
                    from eden.tenancy.context import spawn_safe_task
                    spawn_safe_task(_do_log(), name="audit-fallback")
            except RuntimeError:
                # If no loop is running, we can't do background logging.
                # In most Eden cases, we are in an async web request.
                pass
    except Exception as e:
        logger.debug(f"Failed to schedule audit log: {e}")

def _make_json_safe(val: Any) -> Any:
    """JSON serialization helper."""
    import uuid
    from datetime import datetime
    
    if isinstance(val, (str, int, float, bool, type(None))):
        return val
    if isinstance(val, uuid.UUID):
        return str(val)
    if isinstance(val, datetime):
        return val.isoformat()
    if isinstance(val, (dict, list, tuple, set)):
        # Nested structures handled shallowly or stringified
        return str(val)
    return str(val)


async def audit_log(
    action: str,
    resource: str,
    details: Optional[Dict[str, Any]] = None,
    request: Any = None
) -> AuditLog:
    """
    Manually record a business event.
    """
    user_id = None
    if request and hasattr(request, "state") and hasattr(request.state, "user"):
        user = request.state.user
        if user:
            user_id = str(getattr(user, "id", user))
    elif not request:
        user = get_user()
        if user:
            user_id = str(getattr(user, "id", user))
            
    return await AuditLog.create(
        user_id=user_id,
        action=action,
        model_name=resource,
        record_id="N/A",
        changes=details,
        timestamp=datetime.utcnow()
    )

__all__ = ["AuditLog", "AuditableMixin", "audit_log"]

