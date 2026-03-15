from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from typing import Any, Dict, Set, Optional, Union, List

from starlette.websockets import WebSocket, WebSocketState, WebSocketDisconnect

logger = logging.getLogger("eden.websocket")

class ConnectionManager:
    """
    Manages active WebSocket connections with support for channels and rooms.
    
    This unifies the previous RealTimeManager and ConnectionManager into a single,
    robust implementation.
    """
    def __init__(self) -> None:
        # channel_name -> set of websockets
        self._channels: dict[str, set[WebSocket]] = defaultdict(set)
        # websocket -> set of channel_names
        self._socket_channels: dict[WebSocket, set[str]] = defaultdict(set)
        
        # User-specific tracking for isolation
        self._user_sockets: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, websocket: WebSocket, user_id: str | None = None) -> None:
        """Accept and register a WebSocket connection."""
        if websocket.client_state == WebSocketState.CONNECTING:
            await websocket.accept()
        
        self._socket_channels[websocket] = set()
        if user_id:
            self._user_sockets[str(user_id)].add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        """Clean up on disconnect."""
        # Remove from all channels
        channels = self._socket_channels.pop(websocket, set())
        for channel in channels:
            self._channels[channel].discard(websocket)
            if not self._channels[channel]:
                del self._channels[channel]
        
        # Remove from user tracking
        for user_id, sockets in list(self._user_sockets.items()):
            sockets.discard(websocket)
            if not sockets:
                del self._user_sockets[user_id]

    async def subscribe(self, websocket: WebSocket, channel: str) -> None:
        """Subscribe a websocket to a channel (or 'room')."""
        self._channels[channel].add(websocket)
        self._socket_channels[websocket].add(channel)

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
        exclude: WebSocket | None = None
    ) -> None:
        """Broadcast a message to all subscribers of a channel."""
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

    def count(self) -> int:
        """Return total number of active connections."""
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
        """List all channels with active subscribers."""
        return list(self._channels.keys())

# Global instance for easy access
connection_manager = ConnectionManager()
