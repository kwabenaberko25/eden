import asyncio
import contextvars
from typing import Any
from sqlalchemy import event
from sqlalchemy.orm import Session
from sqlalchemy.orm.session import object_session

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

def _queue_broadcast(target, event_type: str):
    """Queue the broadcast onto the current session so it can be emitted safely after commit."""
    if not getattr(target, "__reactive__", False):
        return
        
    channels = get_reactive_channels(target)
    if not channels:
        return
        
    data = extract_reactive_data(target)
    
    session = object_session(target)
    if session is not None:
        if "pending_broadcasts" not in session.info:
            session.info["pending_broadcasts"] = []
        session.info["pending_broadcasts"].append((channels, event_type, data))
    else:
        # Fallback if no session found (rare during flush), try to emit directly
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                ctx = contextvars.copy_context()
                loop.create_task(ctx.run(_async_broadcast, channels, event_type, data))
        except (RuntimeError, NameError):
            pass

def _emit_pending_broadcasts(session):
    """Fire all queued broadcasts and clear the queue."""
    pending = session.info.pop("pending_broadcasts", [])
    if not pending:
        return
        
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            ctx = contextvars.copy_context()
            for channels, event_type, data in pending:
                loop.create_task(ctx.run(_async_broadcast, channels, event_type, data))
    except (RuntimeError, NameError):
        pass

def register_listeners(model_cls: type):
    """Register all database event listeners for the given model class."""
    
    @event.listens_for(model_cls, "after_insert", propagate=True)
    def after_insert(mapper, connection, target):
        _queue_broadcast(target, "created")

    @event.listens_for(model_cls, "after_update", propagate=True)
    def after_update(mapper, connection, target):
        _queue_broadcast(target, "updated")

    @event.listens_for(model_cls, "after_delete", propagate=True)
    def after_delete(mapper, connection, target):
        _queue_broadcast(target, "deleted")

# Register global session hooks to handle the queued broadcasts
@event.listens_for(Session, "after_commit")
def handle_after_commit(session):
    _emit_pending_broadcasts(session)

@event.listens_for(Session, "after_rollback")
def handle_after_rollback(session):
    session.info.pop("pending_broadcasts", None)
