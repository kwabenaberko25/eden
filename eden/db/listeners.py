
import asyncio
import contextvars
from typing import Any
from sqlalchemy import event

from eden.db.reactive import get_reactive_channels, extract_reactive_data

async def _async_broadcast(channels: list[str], event_type: str, data: dict):
    """Bridge to the unified ConnectionManager for async-safe broadcasting."""
    try:
        from eden.websocket import connection_manager
        
        # Avoid circular dependencies or broadcast during shutdown
        if not connection_manager:
            return

        for channel in channels:
            await connection_manager.broadcast({
                "event": event_type,
                "channel": channel,
                "data": data
            }, channel=channel)
    except Exception as e:
        # We don't want to crash the main request thread on broadcast failure
        import logging
        logging.getLogger("eden.db").debug(f"Reactive broadcast failed: {e}")

def _trigger_broadcast(mapper, connection, target, event_type: str):
    """Sync listener that triggers the async broadcast if the model is marked as @reactive."""
    if not getattr(target, "__reactive__", False):
        return
        
    channels = get_reactive_channels(target)
    if not channels:
        return
        
    data = extract_reactive_data(target)
    
    # Use the current event loop if it exists to run the broadcast
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            # Create a context snapshot for the background task to survive request end
            ctx = contextvars.copy_context()
            loop.create_task(ctx.run(_async_broadcast, channels, event_type, data))
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
