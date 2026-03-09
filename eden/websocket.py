"""
Eden — WebSocket Support

Provides WebSocket handling with room-based messaging and
decorator-driven API, integrating with Eden's routing system.

Usage:
    from eden.websocket import WebSocketRouter

    ws = WebSocketRouter()

    @ws.on("chat")
    async def handle_chat(socket, data):
        await socket.send_json({"echo": data})

    ws.mount(app)
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import Any, Callable

from starlette.websockets import WebSocket, WebSocketDisconnect


__all__ = [
    "WebSocket",
    "WebSocketDisconnect",
    "ConnectionManager",
    "WebSocketRouter",
]


class ConnectionManager:
    """Manages active WebSocket connections with room support."""

    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, websocket: WebSocket, room: str = "default") -> None:
        """Accept and register a WebSocket connection."""
        await websocket.accept()
        self._connections[room].add(websocket)

    def disconnect(self, websocket: WebSocket, room: str = "default") -> None:
        """Remove a WebSocket connection from a room."""
        self._connections[room].discard(websocket)
        if not self._connections[room]:
            del self._connections[room]

    async def broadcast(self, message: Any, room: str = "default") -> None:
        """Send a message to all connections in a room."""
        dead = []
        for ws in self._connections.get(room, set()):
            try:
                if isinstance(message, dict):
                    await ws.send_json(message)
                else:
                    await ws.send_text(str(message))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections[room].discard(ws)

    async def send_to(self, websocket: WebSocket, message: Any) -> None:
        """Send a message to a specific connection."""
        if isinstance(message, dict):
            await websocket.send_json(message)
        else:
            await websocket.send_text(str(message))

    @property
    def rooms(self) -> list[str]:
        """List all active rooms."""
        return list(self._connections.keys())

    def count(self, room: str = "default") -> int:
        """Count connections in a room."""
        return len(self._connections.get(room, set()))


class WebSocketRouter:
    """
    Decorator-based WebSocket router with event handling.

    Usage:
        ws = WebSocketRouter(prefix="/ws")

        @ws.on("message")
        async def on_message(socket, data, manager):
            await manager.broadcast(data, room="chat")

        ws.mount(app)
    """

    def __init__(self, prefix: str = "/ws") -> None:
        self.prefix = prefix.rstrip("/")
        self.manager = ConnectionManager()
        self._handlers: dict[str, Callable] = {}
        self._on_connect: Callable | None = None
        self._on_disconnect: Callable | None = None

    def on(self, event: str) -> Callable:
        """Register a handler for a named event."""
        def decorator(func: Callable) -> Callable:
            self._handlers[event] = func
            return func
        return decorator

    def on_connect(self, func: Callable) -> Callable:
        """Register a handler called when a client connects."""
        self._on_connect = func
        return func

    def on_disconnect(self, func: Callable) -> Callable:
        """Register a handler called when a client disconnects."""
        self._on_disconnect = func
        return func

    def mount(self, app: Any, path: str | None = None) -> None:
        """Mount WebSocket endpoint onto an Eden app."""
        ws_path = path or f"{self.prefix}/{{room}}"
        router = self

        from starlette.routing import WebSocketRoute

        async def ws_endpoint(websocket: WebSocket) -> None:
            room = websocket.path_params.get("room", "default")
            await router.manager.connect(websocket, room)

            if router._on_connect:
                await router._on_connect(websocket, router.manager)

            try:
                while True:
                    raw = await websocket.receive_text()
                    try:
                        data = json.loads(raw)
                    except json.JSONDecodeError:
                        data = {"message": raw}

                    event = data.get("event", "message") if isinstance(data, dict) else "message"
                    handler = router._handlers.get(event)
                    if handler:
                        await handler(websocket, data, router.manager)
                    else:
                        # Default: echo back
                        await websocket.send_json({"event": event, "data": data})

            except WebSocketDisconnect:
                router.manager.disconnect(websocket, room)
                if router._on_disconnect:
                    await router._on_disconnect(websocket, router.manager)

        # Store route for inclusion
        self._ws_route = WebSocketRoute(ws_path, ws_endpoint, name="eden_websocket")

        # Register with Starlette app directly during build
        if hasattr(app, "_ws_routes"):
            app._ws_routes.append(self._ws_route)
        else:
            app._ws_routes = [self._ws_route]
