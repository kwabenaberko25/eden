from __future__ import annotations

import json
import logging
from typing import Any, Callable, Dict, Optional, Union

from starlette.websockets import WebSocket, WebSocketDisconnect

from eden.websocket.manager import ConnectionManager, connection_manager as global_manager
from eden.routing import WebSocketRoute

logger = logging.getLogger("eden.websocket")

class WebSocketRouter:
    """
    Decorator-based WebSocket router with event handling and built-in security.
    
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
        self._ws_routes: list[WebSocketRoute] = []

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

    @property
    def routes(self) -> list[WebSocketRoute]:
        """Expose registered WebSocket routes."""
        if self._ws_routes:
            return self._ws_routes

        ws_path = f"{self.prefix}/{{channel}}"
        route = WebSocketRoute(ws_path, self._build_endpoint(), name=f"ws_{self.prefix.strip('/')}")
        return [route]

    async def _validate_subscription(self, websocket: WebSocket, channel: str) -> bool:
        """
        Securely validate if a client is permitted to subscribe to a specific channel.
        
        Enforces isolation for:
        - tenant:{tenant_id}:{table}
        - org:{org_id}:{table}
        """
        if ":" not in channel:
            # Allow public/generic channels for now
            return True
            
        parts = channel.split(":")
        prefix = parts[0]
        
        if prefix not in ("tenant", "org"):
            # Not a framework-protected channel prefix
            return True
            
        user = websocket.scope.get("user")
        
        # Superuser bypass
        if user and getattr(user, "is_superuser", False):
            return True
            
        if prefix == "tenant":
            if len(parts) < 2: return False
            target_tenant_id = parts[1]
            return str(getattr(user, "tenant_id", "")) == target_tenant_id
            
        if prefix == "org":
            if len(parts) < 2: return False
            target_org_id = parts[1]
            return str(getattr(user, "organization_id", "")) == target_org_id
            
        return True

    async def _handle_websocket(self, websocket: WebSocket) -> None:
        """Unified WebSocket connection and message loop handler."""
        channel = websocket.path_params.get("channel", "default")
        
        # 1. Authentication
        user = websocket.scope.get("user")
        is_authenticated = user and getattr(user, "is_authenticated", False)
        
        if self.auth_required and not is_authenticated:
            # Try to recover user from session if Starlette hasn't populated it
            # (Requires SessionMiddleware to be active)
            session = websocket.scope.get("session")
            if session and "_user_id" in session:
                logger.debug("Attempting to recover user from session for WebSocket...")
                # Future implementation should fetch user here. 
                # For now, we rely on Middleware population.
            
            logger.warning("WebSocket rejected: Authentication required.")
            await websocket.close(code=4003)
            return

        # 2. Validate Initial Channel
        if not await self._validate_subscription(websocket, channel):
            logger.warning(f"WebSocket rejected: Unauthorized subscription to path-channel '{channel}'")
            await websocket.close(code=4003)
            return

        # 3. Connect and Register
        user_id = getattr(user, "id", str(user)) if is_authenticated else None
        await self.manager.connect(websocket, user_id=user_id)
        await self.manager.subscribe(websocket, channel)

        # 4. Trigger on_connect callback
        if self._on_connect:
            try:
                await self._on_connect(websocket, self.manager)
            except Exception as e:
                logger.error(f"Error in on_connect handler: {e}")
                await websocket.close()
                return

        # 5. Message Loop
        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    data = {"event": "message", "data": raw}

                if not isinstance(data, dict):
                    data = {"event": "message", "data": data}

                action = data.get("action")
                event = data.get("event") or action or "message"
                
                # --- Dynamic Subscription Handling ---
                if action == "subscribe":
                    target = data.get("channel")
                    if target:
                        if await self._validate_subscription(websocket, target):
                            await self.manager.subscribe(websocket, target)
                        else:
                            logger.warning(f"WebSocket: Denied subscription to '{target}' for user {user_id}")
                            await websocket.send_json({
                                "event": "error", 
                                "message": f"Unauthorized subscription to {target}"
                            })
                    continue
                
                if action == "unsubscribe":
                    target = data.get("channel")
                    if target:
                        await self.manager.unsubscribe(websocket, target)
                    continue

                # --- Handler Dispatch ---
                handler_data = data.get("data", data)
                handler = self._handlers.get(event)
                if handler:
                    try:
                        await handler(websocket, handler_data, self.manager)
                    except Exception as e:
                        logger.error(f"Error in WebSocket handler '{event}': {e}")
                        if websocket.client_state == 1: # Connected
                            await websocket.send_json({"event": "error", "message": "Internal error"})
                elif action is None:
                    logger.debug(f"No handler for event '{event}'")
        
        except WebSocketDisconnect:
            await self.manager.disconnect(websocket)
            if self._on_disconnect:
                await self._on_disconnect(websocket, self.manager)
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
            await self.manager.disconnect(websocket)

    def _build_endpoint(self) -> Callable:
        """Return the unified handler as a closure for Starlette routing."""
        return self._handle_websocket

    def mount(self, app: Any, path: str | None = None) -> None:
        """Mount WebSocket endpoint onto an Eden app or Router."""
        ws_path = path or f"{self.prefix}/{{channel}}"
        
        # Register with app/router
        if hasattr(app, "add_websocket_route"):
             app.add_websocket_route(ws_path, self._handle_websocket)
        elif hasattr(app, "routes"):
             # For nested Eden Routers
             route = WebSocketRoute(
                path=ws_path, 
                endpoint=self._handle_websocket, 
                name=f"ws_{self.prefix.strip('/')}",
             )
             app.routes.append(route)
        
        if hasattr(app, "_ws_routes"):
            app._ws_routes.append(WebSocketRoute(ws_path, self._handle_websocket))
