"""
Eden — Messaging System (Flash & Real-time)

Provides a Django-like messaging system with both session-based persistence
and real-time WebSocket broadcasting.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator, List, Optional, Union

# Message Levels (matching Django for familiarity)
DEBUG = 10
INFO = 20
SUCCESS = 25
WARNING = 30
ERROR = 40

LEVEL_TAGS = {
    DEBUG: "debug",
    INFO: "info",
    SUCCESS: "success",
    WARNING: "warning",
    ERROR: "error",
}


@dataclass
class Message:
    """A single message for the user."""
    message: str
    level: int = INFO
    extra_tags: str = ""
    sticky: bool = False  # If True, persists until manually dismissed or consumed

    @property
    def level_tag(self) -> str:
        return LEVEL_TAGS.get(self.level, "info")

    def to_dict(self) -> dict[str, Any]:
        return {
            "message": self.message,
            "level": self.level,
            "level_tag": self.level_tag,
            "extra_tags": self.extra_tags,
            "sticky": self.sticky,
        }


class MessageContainer:
    """
    Container for messages during a request.
    Handles session storage and WebSocket broadcasting.
    """
    SESSION_KEY = "_eden_messages"  # Legacy compatibility
    def __init__(self, request: Any) -> None:
        from eden.config import get_config
        self.config = get_config()
        self.session_key = self.config.messages_session_key
        
        self.request = request
        self._queued_messages: List[Message] = []
        self._loaded_messages: List[Message] = []
        self._loaded = False

    def _load(self) -> None:
        """Load messages from the session."""
        if self._loaded:
            return
        
        session = getattr(self.request, "session", {})
        if self.session_key in session:
            try:
                # We pop the data, which means it MUST BE SAVED BACK by _save()
                # if not consumed/cleared.
                data = session.pop(self.session_key)
                for item in data:
                    msg = Message(
                        message=item.get("message", ""),
                        level=int(item.get("level", INFO)),
                        extra_tags=item.get("extra_tags", ""),
                        sticky=item.get("sticky", False),
                    )
                    self._loaded_messages.append(msg)
            except (TypeError, ValueError, KeyError):
                pass
        
        self._loaded = True

    def _save(self) -> None:
        """
        Persist unconsumed messages back to the session.
        This is typically called by the MessagesMiddleware at the end of a request.
        """
        if not self._loaded and not self._queued_messages:
            # Nothing to do if we didn't load and have no new messages
            return

        session = getattr(self.request, "session", None)
        if session is None:
            return

        # Prepare unconsumed messages for storage
        # We combine loaded messages (that weren't iterated) and queued messages (new)
        messages_to_save = [m.to_dict() for m in self._loaded_messages + self._queued_messages]
        
        if messages_to_save:
            session[self.session_key] = messages_to_save
        elif self.session_key in session:
            # All messages consumed, clear session key
            del session[self.session_key]

    def add(self, message: str, level: int = INFO, extra_tags: str = "", 
            push: bool = True, channel: Optional[str] = None, 
            allow_duplicates: bool = False, sticky: bool = False) -> None:
        """
        Add a new message and optionally push via WebSocket.
        """
        # Ensure we've loaded existing session messages BEFORE adding new ones
        self._load()

        # Deduplication
        if not allow_duplicates:
            all_messages = self._queued_messages + self._loaded_messages
            if any(m.message == message and m.level == level for m in all_messages):
                return

        msg = Message(message=message, level=level, extra_tags=extra_tags, sticky=sticky)
        self._queued_messages.append(msg)
        
        # Real-time Push via WebSocket
        if push:
            self._push_realtime(msg, channel=channel)

    def _push_realtime(self, message: Message, channel: Optional[str] = None) -> None:
        """
        Attempt to broadcast the message to the user's active WebSocket room 
        or a specific channel.
        """
        try:
            from eden.websocket import connection_manager as manager
            import logging
            ws_logger = logging.getLogger("eden.websocket")
            
            # 1. Determine Channel
            if channel is None:
                user = getattr(self.request, "user", None)
                if user and getattr(user, "is_authenticated", False):
                    # Try common ID attributes
                    user_id = getattr(user, "id", None) or getattr(user, "pk", None)
                    if user_id:
                        channel = f"user_{user_id}"
            
            if not channel:
                return

            # 2. Prepare Payload
            payload = {
                "event": "eden:message",
                "data": message.to_dict()
            }

            # 3. Schedule Broadcast
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                # Schedule as background task to avoid blocking request
                from eden.tenancy.context import spawn_safe_task
                spawn_safe_task(
                    manager.broadcast(payload, channel=channel),
                    name=f"ws-broadcast-{channel}",
                )
            except RuntimeError:
                # No running loop (e.g. in a sync script/shell), log but don't crash
                import logging
                logging.getLogger("eden.messages").debug(
                    f"WebSocket push skipped: No running event loop for channel {channel}"
                )
                
        except ImportError:
            # WebSocket module not available
            pass
        except Exception as e:
            # WebSocket failure should never crash the request, but we should log it
            import logging
            logging.getLogger("eden.messages").warning(f"Failed to push real-time message: {e}")

    def get_by_level(self, level: int) -> List[Message]:
        """Return all messages for a specific level."""
        self._load()
        return [m for m in self._loaded_messages + self._queued_messages if m.level == level]

    def count_by_level(self, level: int) -> int:
        """Return the count of messages for a specific level."""
        return len(self.get_by_level(level))

    def all(self) -> List[Message]:
        """
        Return all messages (loaded + queued) without consuming them.
        Useful for checking status without clearing the flash queue.
        """
        self._load()
        return self._loaded_messages + self._queued_messages

    def debug(self, message: str, **kwargs) -> None:
        """Quick add a DEBUG message."""
        self.add(message, level=DEBUG, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        """Quick add an INFO message."""
        self.add(message, level=INFO, **kwargs)

    def success(self, message: str, **kwargs) -> None:
        """Quick add a SUCCESS message."""
        self.add(message, level=SUCCESS, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Quick add a WARNING message."""
        self.add(message, level=WARNING, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        """Quick add an ERROR message."""
        self.add(message, level=ERROR, **kwargs)

    def __iter__(self) -> Iterator[Message]:
        self._load()
        # Once we iterate, the messages are considered "consumed" (flashed)
        # However, we already popped them from the session in _load()
        for msg in self._loaded_messages:
            yield msg
        for msg in self._queued_messages:
            yield msg
        
        # Clear local buffers but RETAIN sticky ones for session persistence
        self._loaded_messages = [m for m in self._loaded_messages if m.sticky]
        self._queued_messages = [m for m in self._queued_messages if m.sticky]

    def __len__(self) -> int:
        self._load()
        return len(self._loaded_messages) + len(self._queued_messages)

    def __bool__(self) -> bool:
        """Return True if there are any unconsumed messages."""
        return len(self) > 0


def get_messages(request: Optional[Any] = None) -> MessageContainer:
    """
    Retrieve the message container for the current request.
    
    Returns the MessageContainer instance which is both iterable (for templates)
    and has helper methods for adding messages.
    """
    if request is None:
        from eden.context import get_request
        request = get_request()
    
    if not request:
        return MessageContainer(None)
        
    if "_eden_messages" not in request.scope:
        request.scope["_eden_messages"] = MessageContainer(request)
        
    return request.scope["_eden_messages"]


def add_message(message: str, level: int = INFO, request: Optional[Any] = None, **kwargs: Any) -> None:
    """Add a message to the container."""
    get_messages(request).add(message, level=level, **kwargs)


def debug(message: str, request: Optional[Any] = None, **kwargs: Any) -> None:
    """Add a debug message."""
    add_message(message, level=DEBUG, request=request, **kwargs)


def info(message: str, request: Optional[Any] = None, **kwargs: Any) -> None:
    """Add an info message."""
    add_message(message, level=INFO, request=request, **kwargs)


def success(message: str, request: Optional[Any] = None, **kwargs: Any) -> None:
    """Add a success message."""
    add_message(message, level=SUCCESS, request=request, **kwargs)


def warning(message: str, request: Optional[Any] = None, **kwargs: Any) -> None:
    """Add a warning message."""
    add_message(message, level=WARNING, request=request, **kwargs)


def error(message: str, request: Optional[Any] = None, **kwargs: Any) -> None:
    """Add an error message."""
    add_message(message, level=ERROR, request=request, **kwargs)
