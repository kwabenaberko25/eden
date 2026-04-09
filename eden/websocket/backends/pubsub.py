from __future__ import annotations
"""
Eden — WebSocket PubSub Manager
"""


import json
import logging
from typing import Any, Callable, Dict, Optional, Protocol

from starlette.websockets import WebSocket

from eden.core.backends.base import DistributedBackend

logger = logging.getLogger("eden.websocket.pubsub")

class PubSubManager:
    """
    Coordinates distributed WebSocket room broadcasting via a DistributedBackend.
    
    When a message is broadcast to a room on one worker, this manager publishes
    it to the distributed backend. Other workers subscribe to these events and
    forward the messages to their local subscribers.
    """
    
    def __init__(self, backend: DistributedBackend, local_manager: Any) -> None:
        self.backend = backend
        self.local_manager = local_manager
        self._subscribed_channels: set[str] = set()

    async def setup(self) -> None:
        """Start the PubSub manager."""
        # Subscribe to a global broadcast channel if needed, 
        # or we dynamically subscribe as needed?
        # Actually, if we have many rooms, subscribing to all of them globally 
        # is better handled by a single 'ws_broadcast' channel with payloads 
        # indicating the target room.
        await self.backend.subscribe("ws_broadcast", self._on_message)
        logger.debug("WebSocket PubSub manager initialized on channel 'ws_broadcast'")

    async def publish_broadcast(self, room: str, message: Any, exclude_socket_id: str | None = None) -> None:
        """Publish broadcast event to the distributed backend."""
        payload = {
            "room": room,
            "message": message,
            "exclude_socket_id": exclude_socket_id,
        }
        await self.backend.publish("ws_broadcast", payload)

    async def _on_message(self, data: Any) -> None:
        """Handle broadcast message from other workers."""
        if not isinstance(data, dict):
            return
            
        room = data.get("room")
        message = data.get("message")
        exclude_socket_id = data.get("exclude_socket_id")
        
        if not room or message is None:
            return
            
        # Broadcast to local subscribers
        # We need a way to identify the local socket to exclude if necessary.
        # However, it's easier to just broadcast locally and let the exclude logic 
        # handle it relative to this specific worker.
        # Actually, if we broadcast on Worker A, it publishes to Redis.
        # Worker A also receives its own message if it's subscribed to Redis.
        # To avoid double broadcasting on Worker A, we need a worker ID or common identifier.
        
        # Wait, if we use local_manager.broadcast directly, we might double-send.
        # Actually, let's modify ConnectionManager to handle this.
        pass
