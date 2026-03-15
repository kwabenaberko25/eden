"""
Eden — WebSocket Authentication

Provides utilities for secure WebSocket connections, including token and 
cookie-based authentication.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, Optional, Callable

from starlette.websockets import WebSocket

@dataclass
class ConnectionState:
    """Stores WebSocket connection state for recovery."""
    user_id: str
    room: str
    connected_at: str
    metadata: Dict[str, Any]
    
    def to_json(self) -> str:
        """Serialize state to JSON."""
        return json.dumps(asdict(self))
    
    @classmethod
    def from_json(cls, data: str) -> "ConnectionState":
        """Deserialize state from JSON."""
        return cls(**json.loads(data))


class AuthenticatedWebSocket:
    """
    WebSocket with built-in authentication and reconnection support.
    """
    
    def __init__(self, websocket: WebSocket, app: Any):
        """
        Initialize authenticated WebSocket.
        """
        self.websocket = websocket
        self.app = app
        self.user = None
        self.room: Optional[str] = None
        self.state: Optional[ConnectionState] = None
        self._message_handlers: Dict[str, Callable] = {}
        self._active = False
    
    async def authenticate_with_token(self, token_name: str = "token") -> Any:
        """
        Authenticate connection using token from query string.
        """
        token = self.websocket.query_params.get(token_name)
        if not token:
            raise AuthenticationError("No authentication token provided")
        
        user = await self._validate_token(token)
        if not user:
            raise AuthenticationError("Invalid or expired token")
        
        self.user = user
        return user
    
    async def authenticate_with_cookie(self) -> Any:
        """
        Authenticate using session cookie.
        """
        session = getattr(self.websocket, "session", {})
        user_id = session.get("user_id")
        
        if not user_id:
            raise AuthenticationError("No session found")
        
        user = await self._load_user(user_id)
        if not user:
            raise AuthenticationError("User not found")
        
        self.user = user
        return user
    
    async def _validate_token(self, token: str) -> Optional[Any]:
        """Placeholder for token validation."""
        return None
    
    async def _load_user(self, user_id: str) -> Optional[Any]:
        """Placeholder for user loading."""
        return None
    
    async def accept(self, subprotocol: str | None = None) -> None:
        """Accept the WebSocket connection."""
        await self.websocket.accept(subprotocol=subprotocol)
        self._active = True
    
    async def send_json(self, data: Dict[str, Any]) -> None:
        """Send JSON message to client."""
        if not self._active:
            raise ConnectionError("WebSocket not connected")
        await self.websocket.send_json(data)
    
    async def send_text(self, text: str) -> None:
        """Send text message to client."""
        if not self._active:
            raise ConnectionError("WebSocket not connected")
        await self.websocket.send_text(text)
    
    async def receive_json(self) -> Dict[str, Any]:
        """Receive JSON message from client."""
        try:
            return await self.websocket.receive_json()
        except Exception as e:
            raise ConnectionError(f"Failed to receive message: {e}")
    
    async def receive_text(self) -> str:
        """Receive text message from client."""
        try:
            return await self.websocket.receive_text()
        except Exception as e:
            raise ConnectionError(f"Failed to receive message: {e}")
    
    async def close(self, code: int = 1000) -> None:
        """Close the WebSocket connection."""
        self._active = False
        await self.websocket.close(code=code)
    
    def on_message(self, message_type: str):
        """Register a message handler."""
        def decorator(func: Callable) -> Callable:
            self._message_handlers[message_type] = func
            return func
        return decorator
    
    async def save_state(self) -> str:
        """Save connection state for reconnection."""
        self.state = ConnectionState(
            user_id=str(self.user.id) if self.user else "unknown",
            room=self.room or "",
            connected_at=datetime.now().isoformat(),
            metadata={}
        )
        return self.state.to_json()
    
    async def restore_state(self, state_json: str) -> None:
        """Restore connection state after reconnection."""
        try:
            self.state = ConnectionState.from_json(state_json)
            self.room = self.state.room
        except Exception as e:
            # log or handle
            pass
    
    async def broadcast_message(
        self,
        message: str,
        exclude_self: bool = False
    ) -> None:
        """
        Broadcast message utility.
        Note: In real usage, use connection_manager.broadcast
        """
        data = {
            "type": "broadcast",
            "message": message,
            "from_user": getattr(self.user, "id", None),
            "timestamp": datetime.now().isoformat()
        }
        await self.send_json(data)


class AuthenticationError(Exception):
    """Raised when WebSocket authentication fails."""
    pass


class ConnectionError(Exception):
    """Raised when WebSocket connection error occurs."""
    pass
