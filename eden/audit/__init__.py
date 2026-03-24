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
from eden.context import get_user

logger = logging.getLogger("eden.audit")

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
        for attr in insp.attrs:
            # Skip relationships and internal state
            if not hasattr(attr, "key"):
                continue
            
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

    # Capture user_id from context
    user = get_user()
    user_id = str(getattr(user, "id", user)) if user else None

    # Trigger background task for logging
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            async def _do_log():
                from eden.db.session import reset_session
                # Clear session context in the background task so it opens its own session
                # and doesn't try to reuse the one that is currently flushing.
                reset_session() 
                try:
                    await AuditLog.log(
                        user_id=user_id,
                        action=action,
                        model=target.__class__,
                        record_id=record_id,
                        changes=changes
                    )
                except Exception as exc:
                    logger.warning(f"Background audit log failed: {exc}")

            asyncio.create_task(_do_log())
    except (RuntimeError, NameError):
        pass

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

