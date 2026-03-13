"""
Eden WebSocket authentication and real-time communication.

Warning: There's both a websocket.py module and a websocket/ package.
This __init__.py re-exports from both to maintain a clean API.
"""

# Re-export core WebSocket classes from Starlette
from starlette.websockets import WebSocket, WebSocketDisconnect

# Local authentication/connection management
from .auth import (
    AuthenticatedWebSocket,
    ConnectionState,
    AuthenticationError,
    ConnectionError,
    connection_manager,
)

# WebSocketRouter and ConnectionManager are defined in ../websocket.py
# We need to import them carefully since we're a package
import sys
from pathlib import Path

# Import from the parent websocket.py module (not this package)
parent_module_path = Path(__file__).parent.parent / "websocket.py"
import importlib.util
spec = importlib.util.spec_from_file_location("_eden_websocket_module", parent_module_path)
_websocket_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_websocket_module)

WebSocketRouter = _websocket_module.WebSocketRouter
ConnectionManager = _websocket_module.ConnectionManager

__all__ = [
    "WebSocket",
    "WebSocketDisconnect",
    "WebSocketRouter",
    "ConnectionManager",
    "AuthenticatedWebSocket",
    "ConnectionState",
    "AuthenticationError",
    "ConnectionError",
    "connection_manager",
]
