from datetime import datetime
from typing import Any
from eden.db import Model, StringField, TextField, DateTimeField, JSONField, UUIDField, AllowPublic
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
    async def log(cls, user_id: str | None, action: str, model: Any, record_id: str, changes: dict | None = None, correlation_id: str | None = None):
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
