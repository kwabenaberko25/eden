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
                sticky_messages = []
                data = session.pop(self.session_key)
                for item in data:
                    msg = Message(
                        message=item.get("message", ""),
                        level=int(item.get("level", INFO)),
                        extra_tags=item.get("extra_tags", ""),
                        sticky=item.get("sticky", False),
                    )
                    self._loaded_messages.append(msg)
                    if msg.sticky:
                        sticky_messages.append(msg.to_dict())
                
                # If we have sticky messages, ensure they stay in the session
                if sticky_messages:
                    session = getattr(self.request, "session", None)
                    if session is not None:
                        existing = session.get(self.session_key, [])
                        session[self.session_key] = existing + sticky_messages
            except (TypeError, ValueError, KeyError):
                pass
        
        self._loaded = True

    def add(self, message: str, level: int = INFO, extra_tags: str = "", 
            push: bool = True, channel: Optional[str] = None, 
            allow_duplicates: bool = False, sticky: bool = False) -> None:
        """
        Add a new message and optionally push via WebSocket.
        """
        # Ensure we've loaded existing session messages BEFORE adding new ones
        # to prevent double-loading our own messages if _load is called later.
        self._load()

        # Deduplication (checks both local queue and loaded session messages)
        if not allow_duplicates:
            all_messages = self._queued_messages + self._loaded_messages
            if any(m.message == message and m.level == level for m in all_messages):
                return

        msg = Message(message=message, level=level, extra_tags=extra_tags, sticky=sticky)
        self._queued_messages.append(msg)
        
        # Persist to session immediately (Flash pattern)
        session = getattr(self.request, "session", None)
        if session is not None:
            messages = session.get(self.session_key, [])
            messages.append(msg.to_dict())
            session[self.session_key] = messages

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
                loop.create_task(manager.broadcast(payload, channel=channel))
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
        
        # Clear local buffers
        self._loaded_messages = []
        self._queued_messages = []

    def __len__(self) -> int:
        self._load()
        return len(self._loaded_messages) + len(self._queued_messages)

    def __bool__(self) -> bool:
        return len(self) > 0


def get_messages(request: Optional[Any] = None) -> Union[MessageContainer, Iterator[Message]]:
    """
    Retrieve the message container for the current request.
    
    Returns the MessageContainer instance which is both iterable (for templates)
    and has helper methods for adding messages.
    """
    if request is None:
        from eden.context import get_request
        request = get_request()
    
    if not request:
        return iter([])
        
    if not hasattr(request, "_messages"):
        request._messages = MessageContainer(request)
        
    return request._messages
