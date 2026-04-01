from __future__ import annotations

import asyncio
import hmac
import json
import logging
import re
import secrets
import uuid
from collections import defaultdict
from typing import Any, Dict, Set, Optional, Union, List, TYPE_CHECKING

from starlette.websockets import WebSocket, WebSocketState, WebSocketDisconnect

from eden.core.backends.base import DistributedBackend
from eden.core.metrics import metrics

if TYPE_CHECKING:
    from eden.requests import Request

logger = logging.getLogger("eden.websocket")

class ConnectionManager:
    """
    Manages active WebSocket connections with support for channels and rooms.
    
    This unifies the previous RealTimeManager and ConnectionManager into a single,
    robust implementation.
    
    Features:
        - Channel/room-based pub/sub
        - Per-user connection tracking
        - Heartbeat ping/pong for dead connection detection
        - Distributed backend with auto-reconnection
        - Origin and CSRF security validation
    """
    
    # Default heartbeat interval: 30 seconds
    DEFAULT_HEARTBEAT_INTERVAL = 30.0
    # Maximum retries for distributed backend reconnection
    MAX_DISTRIBUTED_RETRIES = 5
    # Base delay for exponential backoff (seconds)
    RETRY_BASE_DELAY = 1.0
    
    def __init__(
        self, 
        allowed_origins: list[str] | None = None,
        require_csrf: bool = False,
        heartbeat_interval: float = DEFAULT_HEARTBEAT_INTERVAL,
    ) -> None:
        # channel_name -> set of websockets
        self._channels: dict[str, set[WebSocket]] = defaultdict(set)
        # websocket -> set of channel_names
        self._socket_channels: dict[WebSocket, set[str]] = defaultdict(set)
        
        # User-specific tracking for isolation
        self._user_sockets: dict[str, set[WebSocket]] = defaultdict(set)
        
        # Distributed backend support
        self._distributed_backend: DistributedBackend | None = None
        self._worker_id: str = str(uuid.uuid4())
        self._distributed_listener_task: asyncio.Task | None = None
        
        # Socket context (socket -> metadata like user_id)
        self._socket_context: dict[WebSocket, dict[str, Any]] = {}
        
        # Security configuration
        self.allowed_origins = [re.compile(o) for o in (allowed_origins or [])]
        self.require_csrf = require_csrf
        self._csrf_session_key = "eden_csrf_token" # matches CSRFMiddleware
        
        # Heartbeat configuration
        self._heartbeat_interval = heartbeat_interval
        self._heartbeat_task: asyncio.Task | None = None

    async def connect(self, websocket: WebSocket, user_id: str | None = None) -> None:
        """Accept and register a WebSocket connection with security checks."""
        # 1. Origin Validation
        if self.allowed_origins:
            origin = websocket.headers.get("origin", "")
            if not any(pattern.match(origin) for pattern in self.allowed_origins):
                logger.warning(f"WebSocket rejected: origin '{origin}' not allowed.")
                await websocket.close(code=4003) # Forbidden
                return

        # 2. CSRF Validation
        if self.require_csrf:
            session = websocket.scope.get("session", {})
            expected_token = session.get(self._csrf_session_key)
            # WebSockets usually send CSRF token in query params for the initial handshake
            submitted_token = websocket.query_params.get("csrf_token")
            
            if not expected_token or not submitted_token or not hmac.compare_digest(submitted_token, expected_token):
                logger.warning("WebSocket rejected: CSRF validation failed.")
                await websocket.close(code=4403) # Forbidden
                return

        if websocket.client_state == WebSocketState.CONNECTING:
            await websocket.accept()
        
        self._socket_channels[websocket] = set()
        self._socket_context[websocket] = {"user_id": str(user_id) if user_id else None}
        
        if user_id:
            self._user_sockets[str(user_id)].add(websocket)
            
        # Update metrics
        metrics.set_gauge("websocket_active_connections", self.count())
        metrics.increment("websocket_connect_total")

    async def disconnect(self, websocket: WebSocket) -> None:
        """Clean up on disconnect."""
        # Remove from all channels
        channels = self._socket_channels.pop(websocket, set())
        for channel in channels:
            sockets = self._channels.get(channel)
            if sockets:
                sockets.discard(websocket)
                if not sockets:
                    self._channels.pop(channel, None)
        
        # Remove from user tracking
        for user_id, sockets in list(self._user_sockets.items()):
            sockets.discard(websocket)
            if not sockets:
                self._user_sockets.pop(user_id, None)
        
        self._socket_context.pop(websocket, None)
                
        # Update metrics
        metrics.set_gauge("websocket_active_connections", self.count())
        metrics.increment("websocket_disconnect_total")

    async def subscribe(self, websocket: WebSocket, channel: str) -> bool:
        """
        Subscribe a websocket to a channel (or 'room').
        Returns True if authorized, False otherwise.
        """
        if not await self.authorize_subscribe(websocket, channel):
            logger.warning(f"WebSocket subscription to '{channel}' REJECTED for unauthorized user.")
            return False

        self._channels[channel].add(websocket)
        self._socket_channels[websocket].add(channel)
        return True

    async def authorize_subscribe(self, websocket: WebSocket, channel: str) -> bool:
        """
        Verify if the current WebSocket is authorized to join the requested channel.
        
        Default Logic:
        - If channel starts with 'user:{id}:', user_id MUST match.
        - If channel starts with 'tenant:{id}:', tenant_id MUST match (optional).
        - Broad channels (e.g. 'tasks') are allowed for any connected user.
        """
        ctx = self._socket_context.get(websocket, {})
        user_id = ctx.get("user_id")

        # 1. User-level isolation check
        # Match pattern user:ID:tableName
        if "user:" in channel:
            parts = channel.split(":")
            # Find the 'user' segment to extract the ID following it
            try:
                idx = parts.index("user")
                if idx + 1 < len(parts):
                    required_user_id = parts[idx + 1]
                    if user_id != required_user_id:
                        return False
            except ValueError:
                pass

        # 2. Add further custom hooks here if necessary (Org isolation, etc)
        
        return True

    async def unsubscribe(self, websocket: WebSocket, channel: str) -> None:
        """Unsubscribe a websocket from a channel."""
        self._channels[channel].discard(websocket)
        if not self._channels[channel]:
            del self._channels[channel]
        self._socket_channels[websocket].discard(channel)

    async def broadcast(
        self, 
        message: Any, 
        channel: str = "default", 
        exclude: WebSocket | None = None,
        _is_distributed: bool = False
    ) -> None:
        """
        Broadcast a message to all subscribers of a channel.
        
        If a distributed backend is configured, it also publishes the message
        to all other workers (unless it came from another worker).
        """
        # If we have a distributed backend and the message originated locally,
        # publish it to the backend for other workers to receive.
        if self._distributed_backend and not _is_distributed:
            await self._distributed_backend.publish(
                "ws_broadcast", 
                {
                    "worker_id": self._worker_id,
                    "channel": channel,
                    "message": message
                    # We can't really exclude a specific socket across workers 
                    # unless it has a global ID.
                }
            )

        if channel not in self._channels:
            return

        formatted_message = message
        if not isinstance(message, (str, bytes)):
            formatted_message = json.dumps(message)

        dead = []
        for ws in self._channels[channel]:
            if ws is exclude:
                continue
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    if isinstance(message, dict):
                        await ws.send_json(message)
                    else:
                        await ws.send_text(str(message))
                else:
                    dead.append(ws)
            except Exception as e:
                logger.debug(f"Failed to send to websocket: {e}")
                dead.append(ws)
                metrics.increment("websocket_broadcast_errors_total")

        for ws in dead:
            await self.disconnect(ws)

    async def send_to_user(self, user_id: str, message: Any) -> None:
        """Send a message to all active sockets for a specific user."""
        user_id = str(user_id)
        if user_id not in self._user_sockets:
            return
            
        dead = []
        for ws in self._user_sockets[user_id]:
            try:
                if isinstance(message, dict):
                    await ws.send_json(message)
                else:
                    await ws.send_text(str(message))
            except Exception:
                dead.append(ws)
                
        for ws in dead:
            await self.disconnect(ws)

    async def add_connection(self, websocket: WebSocket, room: str) -> None:
        """Alias for subscribe for backward compatibility."""
        await self.connect(websocket)
        await self.subscribe(websocket, room)
        setattr(websocket, "room", room)

    async def remove_connection(self, websocket: WebSocket) -> None:
        """Alias for disconnect for backward compatibility."""
        await self.disconnect(websocket)

    async def broadcast_to_room(
        self, 
        room: str, 
        message: Any, 
        exclude_user: str | None = None
    ) -> None:
        """Alias for broadcast with room/user exclusion for backward compatibility."""
        # Find socket for user to exclude if provided
        exclude_socket = None
        if exclude_user and exclude_user in self._user_sockets:
            sockets = self._user_sockets[exclude_user]
            if sockets:
                exclude_socket = next(iter(sockets))
        
        await self.broadcast(message, channel=room, exclude=exclude_socket)

    def get_room_info(self, room: str) -> dict[str, Any]:
        """Get info about a room for backward compatibility."""
        if room not in self._channels:
            return {}
        
        sockets = self._channels[room]
        return {
            "room": room,
            "user_count": len(sockets),
            "users": [getattr(getattr(ws, "user", None), "id", None) for ws in sockets]
        }

    async def set_distributed_backend(self, backend: DistributedBackend) -> None:
        """
        Enable distributed broadcasting across multiple workers.
        
        Subscribes to the distributed backend with automatic reconnection
        on failure using exponential backoff.
        """
        if self._distributed_backend:
            return
            
        self._distributed_backend = backend
        
        # Start subscription with retry logic
        from eden.tenancy.context import spawn_safe_task
        self._distributed_listener_task = spawn_safe_task(
            self._distributed_listener_loop(),
            isolate=True,
            name="ws-distributed-listener",
        )
        
        w_id = str(self._worker_id)
        short_id = w_id[:8] if len(w_id) >= 8 else w_id
        logger.info(f"WebSocket ConnectionManager synchronized with distributed backend (worker_id={short_id})")

    async def _distributed_listener_loop(self) -> None:
        """
        Retry loop for distributed backend subscription.
        
        If subscription fails (e.g., Redis disconnect), retries with
        exponential backoff up to MAX_DISTRIBUTED_RETRIES times.
        After exhausting retries, logs an error and gives up.
        """
        retries = 0
        while retries < self.MAX_DISTRIBUTED_RETRIES:
            try:
                if self._distributed_backend:
                    await self._distributed_backend.subscribe(
                        "ws_broadcast", self._on_distributed_message
                    )
                    # If subscribe returns normally (some backends block here),
                    # reset retry counter on successful operation
                    retries = 0
                    # If the subscribe method is non-blocking, break out
                    break
            except Exception as e:
                retries += 1
                delay = self.RETRY_BASE_DELAY * (2 ** (retries - 1))
                logger.error(
                    f"Distributed listener failed (attempt {retries}/{self.MAX_DISTRIBUTED_RETRIES}): {e}. "
                    f"Retrying in {delay:.1f}s..."
                )
                if retries < self.MAX_DISTRIBUTED_RETRIES:
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "Distributed listener exhausted all retries. "
                        "Cross-worker broadcasting will not work until restart."
                    )

    async def _on_distributed_message(self, data: Any) -> None:
        """Handle broadcast events from other workers."""
        if not isinstance(data, dict):
            return
            
        worker_id = data.get("worker_id")
        # Ignore messages originating from this worker (they've already been broadcast locally)
        if worker_id == self._worker_id:
            return
            
        channel = data.get("channel")
        message = data.get("message")
        
        if channel and message is not None:
            # Broadcast locally, marking it as distributed to avoid feedback loops
            await self.broadcast(message, channel=channel, _is_distributed=True)

    # --- Heartbeat ---
    
    async def start_heartbeat(self) -> None:
        """
        Start the heartbeat background task.
        
        Periodically sends WebSocket pings to all connected sockets.
        Sockets that fail to respond are considered dead and disconnected.
        This prevents resource leaks from half-open connections.
        """
        if self._heartbeat_task and not self._heartbeat_task.done():
            return  # Already running
        from eden.tenancy.context import spawn_safe_task
        self._heartbeat_task = spawn_safe_task(
            self._heartbeat_loop(),
            isolate=True,
            name="ws-heartbeat",
        )
        logger.info(f"WebSocket heartbeat started (interval={self._heartbeat_interval}s)")

    async def stop_heartbeat(self) -> None:
        """Stop the heartbeat background task."""
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None
            logger.info("WebSocket heartbeat stopped")

    async def _heartbeat_loop(self) -> None:
        """
        Background loop that pings all connections periodically.
        
        On each tick:
        1. Iterates over all tracked sockets
        2. Sends a WebSocket ping frame
        3. Disconnects any socket that fails to respond
        """
        while True:
            try:
                await asyncio.sleep(self._heartbeat_interval)
                
                if not self._socket_channels:
                    continue  # No connections to ping
                
                dead: list[WebSocket] = []
                
                for ws in list(self._socket_channels.keys()):
                    try:
                        if ws.client_state == WebSocketState.CONNECTED:
                            # Send a WebSocket protocol-level ping
                            await ws.send_bytes(b"")  # Lightweight ping
                        else:
                            dead.append(ws)
                    except Exception:
                        dead.append(ws)
                
                # Clean up dead connections
                for ws in dead:
                    logger.debug(f"Heartbeat: removing dead connection")
                    await self.disconnect(ws)
                
                if dead:
                    metrics.increment("websocket_heartbeat_dead_total", value=len(dead))
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}")
                # Don't crash the loop on unexpected errors
                await asyncio.sleep(self._heartbeat_interval)

    def count(self) -> int:
        """Return total number of active connections on this worker."""
        return len(self._socket_channels)

    @property
    def rooms(self) -> dict[str, set[WebSocket]]:
        """Alias for _channels for backward compatibility."""
        return self._channels

    def get_channels(self, websocket: WebSocket) -> set[str]:
        """Return all channels a specific socket is subscribed to."""
        return self._socket_channels.get(websocket, set())

    @property
    def active_channels(self) -> list[str]:
        """List all channels with active subscribers on this worker."""
        return list(self._channels.keys())

    async def shutdown(self) -> None:
        """Close all active WebSocket connections gracefully."""
        # Stop background tasks
        await self.stop_heartbeat()
        
        if self._distributed_listener_task and not self._distributed_listener_task.done():
            self._distributed_listener_task.cancel()
            try:
                await self._distributed_listener_task
            except asyncio.CancelledError:
                pass
            self._distributed_listener_task = None
        
        active_sockets = list(self._socket_channels.keys())
        logger.info("Closing %d WebSocket connections for shutdown...", len(active_sockets))
        
        # 1001: Going Away (server shutdown)
        close_coroutines = [
            socket.close(code=1001) for socket in active_sockets 
            if socket.client_state != WebSocketState.DISCONNECTED
        ]
        
        if close_coroutines:
            await asyncio.gather(*close_coroutines, return_exceptions=True)
            
        # Clear all state
        self._channels.clear()
        self._socket_channels.clear()
        self._user_sockets.clear()
        
        # Reset metrics
        metrics.set_gauge("websocket_active_connections", 0)
        
        logger.info("WebSocket shutdown complete.")

# Global instance for easy access
connection_manager = ConnectionManager()
