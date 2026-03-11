from __future__ import annotations
import asyncio
import json
from typing import Any, Dict, Set, Union
from starlette.websockets import WebSocket, WebSocketState

class RealTimeManager:
    """
    Manages WebSocket connections and broadcasts events to relevant channels.
    """
    def __init__(self):
        # channel_name -> set of websockets
        self.channels: Dict[str, Set[WebSocket]] = {}
        # websocket -> set of channel_names
        self.socket_channels: Dict[WebSocket, Set[str]] = {}

    async def connect(self, websocket: WebSocket):
        """Accept a websocket connection."""
        await websocket.accept()
        self.socket_channels[websocket] = set()

    async def disconnect(self, websocket: WebSocket):
        """Clean up on disconnect."""
        channels = self.socket_channels.pop(websocket, set())
        for channel in channels:
            if channel in self.channels:
                self.channels[channel].discard(websocket)
                if not self.channels[channel]:
                    del self.channels[channel]

    async def subscribe(self, websocket: WebSocket, channel: str):
        """Subscribe a websocket to a channel."""
        if channel not in self.channels:
            self.channels[channel] = set()
        self.channels[channel].add(websocket)
        self.socket_channels[websocket].add(channel)

    async def unsubscribe(self, websocket: WebSocket, channel: str):
        """Unsubscribe a websocket from a channel."""
        if channel in self.channels:
            self.channels[channel].discard(websocket)
            if not self.channels[channel]:
                del self.channels[channel]
        if websocket in self.socket_channels:
            self.socket_channels[websocket].discard(channel)

    async def broadcast(self, channel: str, message: Any):
        """Broadcast a message to all subscribers of a channel."""
        if channel not in self.channels:
            return

        if not isinstance(message, str):
            message = json.dumps(message)

        disconnected = []
        for websocket in self.channels[channel]:
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_text(message)
                else:
                    disconnected.append(websocket)
            except Exception:
                disconnected.append(websocket)

        for ws in disconnected:
            await self.disconnect(ws)

# Global instance
manager = RealTimeManager()
