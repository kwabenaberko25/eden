from __future__ import annotations
from typing import Any, List, Optional
from eden.context import get_tenant_id, get_organization_id

def _get_attr_or_item(obj: Any, key: str, default: Any = None) -> Any:
    """Polymorphic helper to get an attribute or key from an object."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    # Pydantic v2
    if hasattr(obj, "model_dump"):
        try:
            return getattr(obj, key, default)
        except Exception as e:
            from eden.logging import get_logger
            get_logger(__name__).error("Silent exception caught: %s", e, exc_info=True)
    return getattr(obj, key, default)

import asyncio
import contextvars

async def broadcast_update(target: Any, event: str = "updated") -> None:
    """
    Manually trigger a reactive broadcast for a model instance.
    
    Routes through the session's pending_broadcasts queue so the broadcast
    only fires after the current transaction commits.
    """
    if target is None:
        return
    
    try:
        from sqlalchemy.orm.session import object_session
        session = object_session(target)
    except Exception:
        session = None
    
    if session is not None:
        # Queue it — will be emitted by handle_after_commit
        from eden.db.listeners import _queue_broadcast
        _queue_broadcast(target, event)
    else:
        # No session context (manual call outside ORM) — broadcast immediately
        channels = get_reactive_channels(target)
        if not channels:
            return
        data = extract_reactive_data(target)
        from eden.db.listeners import _async_broadcast
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                ctx = contextvars.copy_context()
                loop.create_task(ctx.run(_async_broadcast, channels, event, data))
        except (RuntimeError, NameError):
            pass

def get_reactive_channels(target: Any) -> List[str]:
    """
    Generate broadcast channels for a model instance or class.
    Correctly handles tenant and organization isolation prefixes.
    """
    if target is None:
        return []

    # 1. Custom model logic overrides everything
    if hasattr(target, "get_reactive_channels"):
        return target.get_reactive_channels()
    if hasattr(target, "get_sync_channels") and not isinstance(target, type):
        return target.get_sync_channels()

    # 2. Derive base info
    is_type = isinstance(target, type)
    table = _get_attr_or_item(target, "__tablename__")
    
    if not table:
        table = target.__name__.lower() if is_type else target.__class__.__name__.lower()
    
    obj_id = _get_attr_or_item(target, "id") if not is_type else None
    
    channels = []
    prefix = ""
    
    # 3. Handle Isolation Prefixes
    # Check for Tenant isolation
    if _get_attr_or_item(target, "__eden_tenant_isolated__", False):
        tenant_id = _get_attr_or_item(target, "tenant_id") if not is_type else None
        if tenant_id is None:
            tenant_id = get_tenant_id()
        if tenant_id:
            prefix = f"tenant:{tenant_id}:"
    
    # Check for Organization isolation
    elif _get_attr_or_item(target, "__eden_org_isolated__", False):
        org_id = _get_attr_or_item(target, "organization_id") if not is_type else None
        if org_id is None:
            org_id = get_organization_id()
        if org_id:
            prefix = f"org:{org_id}:"

    # 4. Handle Access Control (RLS-aware channels)
    # If the model has AccessControl and the 'read' rule is restrictive (e.g. AllowOwner),
    # we should broadcast and listen on a user-specific channel to prevent data leaks.
    is_restrictive = False
    if not is_type and hasattr(target, "__rbac__"):
        # Use getattr to avoid lint errors on type objects
        rbac = getattr(target, "__rbac__", {})
        read_rule = rbac.get("read")
        if read_rule and getattr(read_rule, "is_restrictive", True):
            # Resolve owner/user ID from target
            owner_id = _get_attr_or_item(target, "user_id")
            if not owner_id and hasattr(read_rule, "field"):
                owner_id = _get_attr_or_item(target, read_rule.field)
            
            if owner_id:
                channels.append(f"{prefix}user:{owner_id}:{table}")
                is_restrictive = True

    # 5. Collection-level channel
    # SECURITY: If the model is restrictive, we SKIP the broad collection channel
    # to prevent data leaks to other users in the same tenant.
    if not is_restrictive:
        channels.append(f"{prefix}{table}")
    
    # 6. Instance-level channel
    # Even if restrictive, we keep the instance channel because subscribing to 
    # a specific ID implies the user might have been granted access.
    if obj_id:
        channels.append(f"{prefix}{table}:{obj_id}")
        
    return channels

def extract_reactive_data(target: Any) -> dict:
    """Extract serializable data for broadcast, respecting field whitelists."""
    # Check for field whitelist
    fields = getattr(target, '__reactive_fields__', None)
    
    if hasattr(target, "model_dump"):
        if fields:
            return target.model_dump(include=set(fields))
        return target.model_dump()
        
    if hasattr(target, "to_dict"):
        data = target.to_dict()
        if fields:
            return {k: v for k, v in data.items() if k in fields}
        return data
        
    # Fallback to __dict__ for SQLAlchemy objects
    data = {
        k: v for k, v in getattr(target, "__dict__", {}).items()
        if not k.startswith('_') and isinstance(v, (str, int, float, bool, type(None)))
    }
    if fields:
        return {k: v for k, v in data.items() if k in fields}
    return data
