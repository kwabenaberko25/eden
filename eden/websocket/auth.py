"""
Eden WebSocket Connection Authentication & Reconnection

Provides secure WebSocket connections with automatic authentication,
reconnection support, and state recovery.

Usage:
    @app.websocket("/ws/chat/{room_id:int}")
    async def chat_connection(websocket: AuthenticatedWebSocket, room_id: int):
        user = await websocket.authenticate_with_token()
        await websocket.accept()
        await websocket.broadcast_message(f"{user.name} joined room {room_id}")
"""

from typing import Optional, Callable, Any, Dict
from dataclasses import dataclass, asdict
from datetime import datetime
import json
import asyncio


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
    
    def __init__(self, websocket, app):
        """
        Initialize authenticated WebSocket.
        
        Args:
            websocket: Starlette WebSocket instance
            app: Eden app instance
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
        
        Args:
            token_name: Query parameter name (default: "token")
        
        Returns:
            Authenticated user object
        
        Raises:
            AuthenticationError: If token invalid or expired
        """
        # Get token from query string
        token = self.websocket.query_params.get(token_name)
        if not token:
            raise AuthenticationError("No authentication token provided")
        
        # Validate token (customize based on your auth system)
        user = await self._validate_token(token)
        if not user:
            raise AuthenticationError("Invalid or expired token")
        
        self.user = user
        return user
    
    async def authenticate_with_cookie(self) -> Any:
        """
        Authenticate using session cookie.
        
        Returns:
            Authenticated user object
        """
        session = self.websocket.session
        user_id = session.get("user_id")
        
        if not user_id:
            raise AuthenticationError("No session found")
        
        # Load user from database
        user = await self._load_user(user_id)
        if not user:
            raise AuthenticationError("User not found")
        
        self.user = user
        return user
    
    async def _validate_token(self, token: str) -> Optional[Any]:
        """
        Validate JWT or session token.
        Override this in your implementation.
        """
        # Example: validate JWT token
        try:
            # jwt.decode(token, self.app.secret_key)
            # Then load user from database
            # return await User.get(decoded["user_id"])
            pass
        except Exception:
            return None
    
    async def _load_user(self, user_id: str) -> Optional[Any]:
        """Load user from database by ID."""
        # Customize based on your User model
        # from eden.auth.models import User
        # return await User.get_or_none(id=user_id)
        pass
    
    async def accept(self, subprotocol: str = None) -> None:
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
    
    async def handle_messages(self) -> None:
        """
        Main loop to handle incoming messages.
        
        Message format:
            {"type": "message_type", "data": {...}}
        """
        try:
            while self._active:
                message = await self.receive_json()
                message_type = message.get("type")
                data = message.get("data", {})
                
                # Route to handler
                if message_type in self._message_handlers:
                    handler = self._message_handlers[message_type]
                    result = handler(self, data)
                    
                    # Handle async handlers
                    if hasattr(result, '__await__'):
                        await result
                
                else:
                    await self.send_json({
                        "type": "error",
                        "message": f"Unknown message type: {message_type}"
                    })
        
        except Exception as e:
            if self._active:
                await self.send_json({
                    "type": "error",
                    "message": str(e)
                })
        
        finally:
            await self.close()
    
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
            # Restore room, metadata, etc.
            self.room = self.state.room
        except Exception as e:
            print(f"Failed to restore state: {e}")
    
    async def broadcast_message(
        self,
        message: str,
        exclude_self: bool = False
    ) -> None:
        """
        Broadcast message to all connected clients in room.
        
        Args:
            message: Message to broadcast
            exclude_self: Don't send back to sender
        """
        # Implementation depends on your session/room management
        # This is a placeholder showing the interface
        data = {
            "type": "broadcast",
            "message": message,
            "from_user": self.user.id if self.user else None,
            "timestamp": datetime.now().isoformat()
        }
        
        await self.send_json(data)


class ConnectionManager:
    """Manager for multiple WebSocket connections (rooms, broadcast)."""
    
    def __init__(self):
        """Initialize connection manager."""
        self.rooms: Dict[str, list[AuthenticatedWebSocket]] = {}
    
    async def add_connection(
        self,
        websocket: AuthenticatedWebSocket,
        room: str
    ) -> None:
        """Register a connection to a room."""
        if room not in self.rooms:
            self.rooms[room] = []
        
        self.rooms[room].append(websocket)
        websocket.room = room
    
    async def remove_connection(
        self,
        websocket: AuthenticatedWebSocket
    ) -> None:
        """Unregister a connection."""
        if websocket.room in self.rooms:
            self.rooms[websocket.room].remove(websocket)
    
    async def broadcast_to_room(
        self,
        room: str,
        message: Dict[str, Any],
        exclude_user: Optional[str] = None
    ) -> None:
        """Broadcast message to all in a room."""
        if room not in self.rooms:
            return
        
        tasks = []
        for ws in self.rooms[room]:
            if exclude_user and ws.user and str(ws.user.id) == exclude_user:
                continue
            
            tasks.append(ws.send_json(message))
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    def get_room_info(self, room: str) -> Dict[str, Any]:
        """Get info about a room."""
        if room not in self.rooms:
            return {}
        
        connections = self.rooms[room]
        return {
            "room": room,
            "user_count": len(connections),
            "users": [
                ws.user.id if ws.user else None
                for ws in connections
            ]
        }


class AuthenticationError(Exception):
    """Raised when WebSocket authentication fails."""
    pass


class ConnectionError(Exception):
    """Raised when WebSocket connection error occurs."""
    pass


# Global connection manager
connection_manager = ConnectionManager()
