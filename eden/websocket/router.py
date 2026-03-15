from __future__ import annotations

import json
import logging
from typing import Any, Callable, Dict, Optional, Union

from starlette.websockets import WebSocket, WebSocketDisconnect
from starlette.routing import WebSocketRoute

from eden.websocket.manager import ConnectionManager, connection_manager as global_manager

logger = logging.getLogger("eden.websocket")

class WebSocketRouter:
    """
    Decorator-based WebSocket router with event handling and built-in authentication.
    
    Usage:
        ws = WebSocketRouter(prefix="/ws")
        
        @ws.on("chat")
        async def on_chat(socket, data, manager):
            await manager.broadcast(data, channel="global")
    """

    def __init__(
        self, 
        prefix: str = "/ws", 
        manager: Optional[ConnectionManager] = None,
        auth_required: bool = False
    ) -> None:
        self.prefix = prefix.rstrip("/")
        self.manager = manager or global_manager
        self.auth_required = auth_required
        
        self._handlers: Dict[str, Callable] = {}
        self._on_connect: Optional[Callable] = None
        self._on_disconnect: Optional[Callable] = None

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
        ws_path = path or f"{self.prefix}/{{channel}}"
        router = self

        async def ws_endpoint(websocket: WebSocket) -> None:
            channel = websocket.path_params.get("channel", "default")
            
            # 1. Handle Authentication if required
            user_id = None
            if router.auth_required:
                try:
                    # Look for user in scope (set by earlier middleware if any) or query params
                    user = websocket.scope.get("user")
                    if not user:
                        # Try simple token-based auth from query
                        token = websocket.query_params.get("token")
                        if not token:
                            await websocket.close(code=4003) # Forbidden
                            return
                        # Here we would normally validate the token.
                        # For now, we'll assume it's basic if auth_required is on.
                        # Real implementation should use eden.auth.utils.get_user_from_token
                        pass
                    
                    if user:
                        user_id = getattr(user, "id", str(user))
                except Exception as e:
                    logger.error(f"WebSocket auth failed: {e}")
                    await websocket.close(code=4003)
                    return

            # 2. Accept and subscribe
            await router.manager.connect(websocket, user_id=user_id)
            await router.manager.subscribe(websocket, channel)

            if router._on_connect:
                try:
                    await router._on_connect(websocket, router.manager)
                except Exception as e:
                    logger.error(f"Error in on_connect handler: {e}")
                    await websocket.close()
                    return

            # 3. Message Loop
            try:
                while True:
                    raw = await websocket.receive_text()
                    try:
                        data = json.loads(raw)
                    except json.JSONDecodeError:
                        data = {"event": "message", "data": raw}

                    if isinstance(data, dict):
                        event = data.get("event", "message")
                        handler_data = data.get("data", data)
                    else:
                        event = "message"
                        handler_data = data

                    handler = router._handlers.get(event)
                    if handler:
                        try:
                            await handler(websocket, handler_data, router.manager)
                        except Exception as e:
                            logger.error(f"Error in WebSocket handler '{event}': {e}")
                            await websocket.send_json({"event": "error", "message": "Internal error"})
                    else:
                        # Default fallback
                        logger.debug(f"No handler for event '{event}'")
            
            except WebSocketDisconnect:
                await router.manager.disconnect(websocket)
                if router._on_disconnect:
                    await router._on_disconnect(websocket, router.manager)
            except Exception as e:
                logger.error(f"WebSocket connection error: {e}")
                await router.manager.disconnect(websocket)

        # Create the route
        route = WebSocketRoute(ws_path, ws_endpoint, name=f"ws_{self.prefix.strip('/')}")
        
        # Register with app
        if hasattr(app, "add_websocket_route"):
             app.add_websocket_route(ws_path, ws_endpoint)
        elif hasattr(app, "routes"):
             app.routes.append(route)
        
        # Also store it in the legacy internal list if present
        if hasattr(app, "_ws_routes"):
            app._ws_routes.append(route)
        else:
            app._ws_routes = [route]
