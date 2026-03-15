"""
Eden — Messaging System (Flash & Real-time)

Provides a Django-like messaging system with both session-based persistence
and real-time WebSocket broadcasting.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator, List

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

    @property
    def level_tag(self) -> str:
        return LEVEL_TAGS.get(self.level, "info")

    def to_dict(self) -> dict[str, Any]:
        return {
            "message": self.message,
            "level": self.level,
            "level_tag": self.level_tag,
            "extra_tags": self.extra_tags,
        }


class MessageContainer:
    """
    Container for messages during a request.
    Handles session storage and WebSocket broadcasting.
    """
    SESSION_KEY = "_eden_messages"

    def __init__(self, request: Any) -> None:
        self.request = request
        self._queued_messages: List[Message] = []
        self._loaded_messages: List[Message] = []
        self._loaded = False

    def _load(self) -> None:
        """Load messages from the session."""
        if self._loaded:
            return
        
        session = getattr(self.request, "session", {})
        if self.SESSION_KEY in session:
            try:
                data = session.pop(self.SESSION_KEY)
                for item in data:
                    self._loaded_messages.append(Message(
                        message=item.get("message", ""),
                        level=int(item.get("level", INFO)),
                        extra_tags=item.get("extra_tags", ""),
                    ))
            except (TypeError, ValueError, KeyError):
                pass
        
        self._loaded = True

    def add(self, message: str, level: int = INFO, extra_tags: str = "", push: bool = True) -> None:
        """Add a new message and optionally push via WebSocket."""
        msg = Message(message=message, level=level, extra_tags=extra_tags)
        self._queued_messages.append(msg)
        
        # Persist to session immediately (Flash pattern)
        session = getattr(self.request, "session", None)
        if session is not None:
            messages = session.get(self.SESSION_KEY, [])
            messages.append(msg.to_dict())
            session[self.SESSION_KEY] = messages

        # Real-time Push via WebSocket
        if push:
            self._push_realtime(msg)

    def _push_realtime(self, message: Message) -> None:
        """Attempt to broadcast the message to the user's active WebSocket room."""
        try:
            from eden.websocket import connection_manager as manager
            user = getattr(self.request, "user", None)
            channel = None
            
            if user and getattr(user, "is_authenticated", False):
                channel = f"user_{user.id}"
            
            if channel:
                payload = {
                    "event": "eden:message",
                    "data": message.to_dict()
                }
                import asyncio
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(manager.broadcast(payload, channel=channel))
                except RuntimeError:
                    # No running loop, maybe in a thread
                    pass
        except Exception:
            # WebSocket failure should never crash the request
            pass

    def debug(self, message: str, **kwargs) -> None:
        self.add(message, level=DEBUG, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        self.add(message, level=INFO, **kwargs)

    def success(self, message: str, **kwargs) -> None:
        self.add(message, level=SUCCESS, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        self.add(message, level=WARNING, **kwargs)

    def error(self, message: str, **kwargs) -> None:
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
