"""
Test suite for Tier 2: WebSocket Authentication

Tests AuthenticatedWebSocket, ConnectionManager, and related functionality.
"""

import pytest
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from eden.websocket.auth import (
    AuthenticatedWebSocket,
    ConnectionManager,
    ConnectionState,
    AuthenticationError,
    ConnectionError,
)


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket."""
    ws = AsyncMock()
    ws.query_params = {"token": "valid_token"}
    ws.session = {"user_id": "user123"}
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    ws.send_text = AsyncMock()
    ws.receive_json = AsyncMock()
    ws.receive_text = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.fixture
def mock_app():
    """Create a mock Eden app."""
    app = MagicMock()
    app.secret_key = "test_secret"
    return app


@pytest.fixture
def authenticated_websocket(mock_websocket, mock_app):
    """Create an AuthenticatedWebSocket instance."""
    return AuthenticatedWebSocket(mock_websocket, mock_app)


class TestConnectionState:
    """Tests for ConnectionState dataclass."""
    
    def test_connection_state_creation(self):
        """Test creating a ConnectionState."""
        state = ConnectionState(
            user_id="user123",
            room="chat_room_1",
            connected_at=datetime.now().isoformat(),
            metadata={}
        )
        
        assert state.user_id == "user123"
        assert state.room == "chat_room_1"
    
    def test_connection_state_json_serialization(self):
        """Test serializing ConnectionState to JSON."""
        state = ConnectionState(
            user_id="user123",
            room="chat_room_1",
            connected_at=datetime.now().isoformat(),
            metadata={"session_id": "abc123"}
        )
        
        json_str = state.to_json()
        
        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert data["user_id"] == "user123"
        assert data["room"] == "chat_room_1"
    
    def test_connection_state_json_deserialization(self):
        """Test deserializing ConnectionState from JSON."""
        original = ConnectionState(
            user_id="user123",
            room="chat_room_1",
            connected_at=datetime(2024, 1, 1, 12, 0).isoformat(),
            metadata={"session_id": "abc123"}
        )
        
        json_str = original.to_json()
        restored = ConnectionState.from_json(json_str)
        
        assert restored.user_id == original.user_id
        assert restored.room == original.room
        assert restored.metadata == original.metadata


class TestAuthenticatedWebSocket:
    """Tests for AuthenticatedWebSocket class."""
    
    @pytest.mark.asyncio
    async def test_initialization(self, authenticated_websocket):
        """Test WebSocket initialization."""
        assert authenticated_websocket.user is None
        assert authenticated_websocket.room is None
        assert authenticated_websocket._active is False
    
    @pytest.mark.asyncio
    async def test_authenticate_with_token(self, authenticated_websocket, mock_websocket):
        """Test token-based authentication."""
        # Mock token validation
        user = MagicMock()
        user.id = "user123"
        user.name = "John Doe"
        
        with patch.object(
            authenticated_websocket,
            "_validate_token",
            new_callable=AsyncMock,
            return_value=user
        ):
            result = await authenticated_websocket.authenticate_with_token()
            
            assert result == user
            assert authenticated_websocket.user == user
    
    @pytest.mark.asyncio
    async def test_authenticate_with_token_missing(self, authenticated_websocket, mock_websocket):
        """Test authentication with missing token."""
        mock_websocket.query_params = {}  # No token
        
        with pytest.raises(AuthenticationError):
            await authenticated_websocket.authenticate_with_token()
    
    @pytest.mark.asyncio
    async def test_authenticate_with_invalid_token(self, authenticated_websocket):
        """Test authentication with invalid token."""
        with patch.object(
            authenticated_websocket,
            "_validate_token",
            new_callable=AsyncMock,
            return_value=None
        ):
            with pytest.raises(AuthenticationError):
                await authenticated_websocket.authenticate_with_token()
    
    @pytest.mark.asyncio
    async def test_authenticate_with_cookie(self, authenticated_websocket):
        """Test session cookie authentication."""
        user = MagicMock()
        user.id = "user123"
        
        with patch.object(
            authenticated_websocket,
            "_load_user",
            new_callable=AsyncMock,
            return_value=user
        ):
            result = await authenticated_websocket.authenticate_with_cookie()
            
            assert result == user
    
    @pytest.mark.asyncio
    async def test_authenticate_with_cookie_no_session(self, authenticated_websocket, mock_websocket):
        """Test cookie auth with no session."""
        mock_websocket.session = {}  # No user_id
        
        with pytest.raises(AuthenticationError):
            await authenticated_websocket.authenticate_with_cookie()
    
    @pytest.mark.asyncio
    async def test_accept_connection(self, authenticated_websocket, mock_websocket):
        """Test accepting a WebSocket connection."""
        await authenticated_websocket.accept()
        
        mock_websocket.accept.assert_called_once()
        assert authenticated_websocket._active is True
    
    @pytest.mark.asyncio
    async def test_send_json(self, authenticated_websocket, mock_websocket):
        """Test sending JSON message."""
        authenticated_websocket._active = True
        
        data = {"type": "message", "text": "hello"}
        await authenticated_websocket.send_json(data)
        
        mock_websocket.send_json.assert_called_once_with(data)
    
    @pytest.mark.asyncio
    async def test_send_json_not_connected(self, authenticated_websocket):
        """Test sending JSON when not connected."""
        authenticated_websocket._active = False
        
        with pytest.raises(ConnectionError):
            await authenticated_websocket.send_json({"data": "test"})
    
    @pytest.mark.asyncio
    async def test_send_text(self, authenticated_websocket, mock_websocket):
        """Test sending text message."""
        authenticated_websocket._active = True
        
        await authenticated_websocket.send_text("hello")
        
        mock_websocket.send_text.assert_called_once_with("hello")
    
    @pytest.mark.asyncio
    async def test_receive_json(self, authenticated_websocket, mock_websocket):
        """Test receiving JSON message."""
        message = {"type": "chat", "text": "hello"}
        mock_websocket.receive_json.return_value = message
        
        result = await authenticated_websocket.receive_json()
        
        assert result == message
    
    @pytest.mark.asyncio
    async def test_receive_text(self, authenticated_websocket, mock_websocket):
        """Test receiving text message."""
        mock_websocket.receive_text.return_value = "hello"
        
        result = await authenticated_websocket.receive_text()
        
        assert result == "hello"
    
    @pytest.mark.asyncio
    async def test_close_connection(self, authenticated_websocket, mock_websocket):
        """Test closing connection."""
        authenticated_websocket._active = True
        
        await authenticated_websocket.close()
        
        mock_websocket.close.assert_called_once()
        assert authenticated_websocket._active is False
    
    @pytest.mark.asyncio
    async def test_message_handler_decorator(self, authenticated_websocket):
        """Test registering message handlers."""
        @authenticated_websocket.on_message("chat")
        async def handle_chat(ws, data):
            pass
        
        assert "chat" in authenticated_websocket._message_handlers
    
    @pytest.mark.asyncio
    async def test_save_state(self, authenticated_websocket):
        """Test saving connection state."""
        user = MagicMock()
        user.id = "user123"
        authenticated_websocket.user = user
        authenticated_websocket.room = "chat_1"
        
        state_json = await authenticated_websocket.save_state()
        
        assert isinstance(state_json, str)
        state_data = json.loads(state_json)
        assert state_data["user_id"] == "user123"
        assert state_data["room"] == "chat_1"
    
    @pytest.mark.asyncio
    async def test_restore_state(self, authenticated_websocket):
        """Test restoring connection state."""
        state = ConnectionState(
            user_id="user123",
            room="chat_1",
            connected_at=datetime.now().isoformat(),
            metadata={}
        )
        
        state_json = state.to_json()
        await authenticated_websocket.restore_state(state_json)
        
        assert authenticated_websocket.state == state
        assert authenticated_websocket.room == "chat_1"
    
    @pytest.mark.asyncio
    async def test_broadcast_message(self, authenticated_websocket, mock_websocket):
        """Test broadcasting message."""
        user = MagicMock()
        user.id = "user123"
        authenticated_websocket.user = user
        authenticated_websocket._active = True
        
        await authenticated_websocket.broadcast_message("hello world")
        
        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert "message" in call_args
        assert call_args["message"] == "hello world"


class TestConnectionManager:
    """Tests for ConnectionManager class."""
    
    @pytest.fixture
    def connection_manager(self):
        """Create a ConnectionManager."""
        return ConnectionManager()
    
    @pytest.mark.asyncio
    async def test_add_connection(self, connection_manager):
        """Test adding a connection to a room."""
        ws = MagicMock()
        ws.room = None
        
        await connection_manager.add_connection(ws, "room_1")
        
        assert "room_1" in connection_manager.rooms
        assert ws in connection_manager.rooms["room_1"]
        assert ws.room == "room_1"
    
    @pytest.mark.asyncio
    async def test_remove_connection(self, connection_manager):
        """Test removing a connection from a room."""
        ws = MagicMock()
        connection_manager.rooms["room_1"] = [ws]
        ws.room = "room_1"
        
        await connection_manager.remove_connection(ws)
        
        assert ws not in connection_manager.rooms["room_1"]
    
    @pytest.mark.asyncio
    async def test_broadcast_to_room(self, connection_manager):
        """Test broadcasting to all in a room."""
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        
        connection_manager.rooms["room_1"] = [ws1, ws2]
        
        message = {"type": "chat", "text": "hello"}
        await connection_manager.broadcast_to_room("room_1", message)
        
        ws1.send_json.assert_called_once()
        ws2.send_json.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_broadcast_exclude_user(self, connection_manager):
        """Test broadcasting with user exclusion."""
        ws1 = AsyncMock()
        ws1.user = MagicMock(id="user1")
        
        ws2 = AsyncMock()
        ws2.user = MagicMock(id="user2")
        
        connection_manager.rooms["room_1"] = [ws1, ws2]
        
        message = {"type": "chat"}
        await connection_manager.broadcast_to_room(
            "room_1",
            message,
            exclude_user="user1"
        )
        
        # ws1 should not receive (excluded)
        # ws2 should receive
        ws2.send_json.assert_called_once()
    
    def test_get_room_info(self, connection_manager):
        """Test getting room information."""
        ws1 = MagicMock()
        ws1.user = MagicMock(id="user1")
        
        ws2 = MagicMock()
        ws2.user = MagicMock(id="user2")
        
        connection_manager.rooms["room_1"] = [ws1, ws2]
        
        info = connection_manager.get_room_info("room_1")
        
        assert info["room"] == "room_1"
        assert info["user_count"] == 2
        assert len(info["users"]) == 2
    
    def test_get_room_info_empty_room(self, connection_manager):
        """Test getting info for non-existent room."""
        info = connection_manager.get_room_info("nonexistent")
        
        assert info == {}


class TestWebSocketIntegration:
    """Integration tests for WebSocket flows."""
    
    @pytest.mark.asyncio
    async def test_authentication_flow(self, authenticated_websocket):
        """Test complete authentication flow."""
        user = MagicMock()
        user.id = "user123"
        
        with patch.object(
            authenticated_websocket,
            "_validate_token",
            new_callable=AsyncMock,
            return_value=user
        ):
            # Authenticate
            auth_user = await authenticated_websocket.authenticate_with_token()
            assert auth_user == user
            
            # Accept connection
            await authenticated_websocket.accept()
            assert authenticated_websocket._active is True
    
    @pytest.mark.asyncio
    async def test_message_handling_flow(self, authenticated_websocket, mock_websocket):
        """Test handling incoming messages."""
        authenticated_websocket._active = True
        
        # Register handler
        @authenticated_websocket.on_message("chat")
        async def handle_chat(ws, data):
            await ws.send_json({"type": "ack"})
        
        # Simulate receiving message
        message = {"type": "chat", "data": {"text": "hello"}}
        mock_websocket.receive_json.return_value = message
        
        # In real scenario, this would be in handle_messages loop
        message_type = message.get("type")
        if message_type in authenticated_websocket._message_handlers:
            handler = authenticated_websocket._message_handlers[message_type]
            await handler(authenticated_websocket, message.get("data", {}))
    
    @pytest.mark.asyncio
    async def test_room_broadcast_flow(self, connection_manager):
        """Test broadcasting in a room."""
        # Create multiple connections
        ws1 = AsyncMock()
        ws1.user = MagicMock(id="user1", name="Alice")
        
        ws2 = AsyncMock()
        ws2.user = MagicMock(id="user2", name="Bob")
        
        # Add to room
        await connection_manager.add_connection(ws1, "chat_1")
        await connection_manager.add_connection(ws2, "chat_1")
        
        # Broadcast message
        msg = {"type": "user_joined", "user": "Alice"}
        await connection_manager.broadcast_to_room("chat_1", msg, exclude_user="user1")
        
        # User 2 should receive
        ws2.send_json.assert_called_once()


class TestWebSocketErrors:
    """Tests for error handling."""
    
    @pytest.mark.asyncio
    async def test_invalid_message_type(self, authenticated_websocket, mock_websocket):
        """Test handling of unknown message types."""
        authenticated_websocket._active = True
        
        # No handler registered for this type
        message = {"type": "unknown", "data": {}}
        mock_websocket.receive_json.return_value = message
        
        # Should send error response
        message_type = message.get("type")
        if message_type not in authenticated_websocket._message_handlers:
            await authenticated_websocket.send_json({
                "type": "error",
                "message": f"Unknown message type: {message_type}"
            })
        
        mock_websocket.send_json.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_message_receive_error(self, authenticated_websocket, mock_websocket):
        """Test handling of receive errors."""
        mock_websocket.receive_json.side_effect = Exception("Connection lost")
        
        with pytest.raises(ConnectionError):
            await authenticated_websocket.receive_json()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
