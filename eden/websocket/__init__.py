"""
Eden — WebSocket Package

Provides a consolidated, robust WebSocket layer with:
- Connection and channel (room) management
- Decorator-based routing
- Built-in authentication support
- User-level isolation
"""

from starlette.websockets import WebSocket, WebSocketDisconnect, WebSocketState

from eden.websocket.manager import ConnectionManager, connection_manager
from eden.websocket.router import WebSocketRouter
from eden.websocket.auth import (
    AuthenticatedWebSocket,
    AuthenticationError,
    ConnectionError,
    ConnectionState,
)

__all__ = [
    "WebSocket",
    "WebSocketDisconnect",
    "WebSocketState",
    "WebSocketRouter",
    "ConnectionManager",
    "connection_manager",
    "AuthenticatedWebSocket",
    "AuthenticationError",
    "ConnectionError",
    "ConnectionState",
]
