
import asyncio
from typing import Any
from sqlalchemy import event

async def _async_broadcast(channels: list[str], event_type: str, data: dict):
    """Bridge to the unified ConnectionManager."""
    from eden.websocket import connection_manager
    for channel in channels:
        await connection_manager.broadcast({
            "event": event_type,
            "data": data
        }, channel=channel)

def _get_reactive_channels(target: Any) -> list[str]:
    """Determine which channels to broadcast to for a given model instance."""
    table_name = target.__tablename__
    channels = [table_name, f"{table_name}:{target.id}"]
    
    # If the model has a custom method for extra channels, call it
    if hasattr(target, "get_sync_channels"):
        channels.extend(target.get_sync_channels())
        
    return channels

def _trigger_broadcast(mapper, connection, target, event_type: str):
    """Sync listener that triggers the async broadcast."""
    if not getattr(target, "__reactive__", False):
        return
        
    channels = _get_reactive_channels(target)
    data = target.model_dump()
    
    # Use the current event loop if it exists to run the broadcast
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            asyncio.create_task(_async_broadcast(channels, event_type, data))
    except (RuntimeError, NameError):
        # Fallback if no loop is running (unlikely in ASGI context)
        pass

def register_listeners(model_cls: type):
    """Register all database event listeners for the given model class."""
    
    @event.listens_for(model_cls, "after_insert", propagate=True)
    def after_insert(mapper, connection, target):
        _trigger_broadcast(mapper, connection, target, "created")

    @event.listens_for(model_cls, "after_update", propagate=True)
    def after_update(mapper, connection, target):
        _trigger_broadcast(mapper, connection, target, "updated")

    @event.listens_for(model_cls, "after_delete", propagate=True)
    def after_delete(mapper, connection, target):
        _trigger_broadcast(mapper, connection, target, "deleted")
