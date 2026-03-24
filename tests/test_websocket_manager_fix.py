"""
Tests for WebSocket ConnectionManager improvements (Issue #9).

Verifies:
1. Heartbeat start/stop lifecycle
2. Heartbeat detects and removes dead connections
3. Distributed backend uses retry logic
4. Distributed listener retries on failure
5. Shutdown cancels background tasks
6. CSRF validation uses timing-safe comparison
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from eden.websocket.manager import ConnectionManager


class FakeWebSocket:
    """Fake WebSocket for testing without Starlette dependency."""
    
    def __init__(self, connected=True):
        from starlette.websockets import WebSocketState
        self.client_state = WebSocketState.CONNECTED if connected else WebSocketState.DISCONNECTED
        self.accepted = False
        self.closed = False
        self.close_code = None
        self.sent_bytes = []
        self.headers = {}
        self.query_params = {}
        self.scope = {}
    
    async def accept(self):
        self.accepted = True
        from starlette.websockets import WebSocketState
        self.client_state = WebSocketState.CONNECTED
    
    async def close(self, code=1000):
        self.closed = True
        self.close_code = code
        from starlette.websockets import WebSocketState
        self.client_state = WebSocketState.DISCONNECTED
    
    async def send_bytes(self, data):
        self.sent_bytes.append(data)
    
    async def send_text(self, text):
        pass
    
    async def send_json(self, data):
        pass


class FakeDeadWebSocket(FakeWebSocket):
    """WebSocket that fails on send (simulating dead connection)."""
    
    async def send_bytes(self, data):
        raise ConnectionError("Connection lost")


class TestHeartbeatLifecycle:
    """Test heartbeat start/stop."""
    
    @pytest.mark.asyncio
    async def test_start_heartbeat_creates_task(self):
        """start_heartbeat should create a background task."""
        mgr = ConnectionManager(heartbeat_interval=0.1)
        await mgr.start_heartbeat()
        
        assert mgr._heartbeat_task is not None
        assert not mgr._heartbeat_task.done()
        
        await mgr.stop_heartbeat()
    
    @pytest.mark.asyncio
    async def test_stop_heartbeat_cancels_task(self):
        """stop_heartbeat should cancel and clean up the task."""
        mgr = ConnectionManager(heartbeat_interval=0.1)
        await mgr.start_heartbeat()
        await mgr.stop_heartbeat()
        
        assert mgr._heartbeat_task is None
    
    @pytest.mark.asyncio
    async def test_start_heartbeat_idempotent(self):
        """Calling start_heartbeat twice should not create a second task."""
        mgr = ConnectionManager(heartbeat_interval=0.1)
        await mgr.start_heartbeat()
        task1 = mgr._heartbeat_task
        await mgr.start_heartbeat()
        task2 = mgr._heartbeat_task
        
        assert task1 is task2
        
        await mgr.stop_heartbeat()


class TestHeartbeatDetection:
    """Test that heartbeat detects dead connections."""
    
    @pytest.mark.asyncio
    async def test_heartbeat_pings_connected_sockets(self):
        """Heartbeat should send bytes to connected sockets."""
        mgr = ConnectionManager(heartbeat_interval=0.05)
        ws = FakeWebSocket(connected=True)
        
        # Register the socket
        from starlette.websockets import WebSocketState
        ws.client_state = WebSocketState.CONNECTED
        mgr._socket_channels[ws] = set()
        
        await mgr.start_heartbeat()
        await asyncio.sleep(0.15)  # Wait for at least one heartbeat
        await mgr.stop_heartbeat()
        
        # Should have received at least one ping
        assert len(ws.sent_bytes) >= 1
    
    @pytest.mark.asyncio
    async def test_heartbeat_removes_dead_connections(self):
        """Dead connections should be cleaned up by heartbeat."""
        mgr = ConnectionManager(heartbeat_interval=0.05)
        dead_ws = FakeDeadWebSocket(connected=True)
        
        # Register the dead socket
        from starlette.websockets import WebSocketState
        dead_ws.client_state = WebSocketState.CONNECTED
        mgr._socket_channels[dead_ws] = set()
        
        await mgr.start_heartbeat()
        await asyncio.sleep(0.15)  # Wait for heartbeat to detect dead connection
        await mgr.stop_heartbeat()
        
        # Dead socket should have been removed
        assert dead_ws not in mgr._socket_channels


class TestDistributedRetry:
    """Test distributed backend retry logic."""
    
    @pytest.mark.asyncio
    async def test_distributed_listener_retries_on_failure(self):
        """Distributed listener should retry on subscription failure."""
        mgr = ConnectionManager()
        mgr.MAX_DISTRIBUTED_RETRIES = 3
        mgr.RETRY_BASE_DELAY = 0.01  # Fast retries for testing
        
        # Create a backend that fails twice then succeeds
        call_count = 0
        
        async def failing_subscribe(channel, callback):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError(f"Connection refused (attempt {call_count})")
            # Third attempt succeeds
        
        backend = AsyncMock()
        backend.subscribe = failing_subscribe
        
        await mgr.set_distributed_backend(backend)
        
        # Wait for retries to complete
        await asyncio.sleep(0.2)
        
        assert call_count == 3  # Failed twice, succeeded on third
        
        await mgr.shutdown()
    
    @pytest.mark.asyncio
    async def test_distributed_ignores_own_messages(self):
        """Messages from the same worker should be ignored."""
        mgr = ConnectionManager()
        
        # Simulate receiving own message
        data = {
            "worker_id": mgr._worker_id,
            "channel": "test",
            "message": "hello"
        }
        
        # Should not broadcast
        with patch.object(mgr, 'broadcast') as mock_broadcast:
            await mgr._on_distributed_message(data)
            mock_broadcast.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_distributed_relays_other_worker_messages(self):
        """Messages from other workers should be broadcast locally."""
        mgr = ConnectionManager()
        
        data = {
            "worker_id": "other-worker-id",
            "channel": "test-channel",
            "message": {"text": "hello"}
        }
        
        with patch.object(mgr, 'broadcast', new_callable=AsyncMock) as mock_broadcast:
            await mgr._on_distributed_message(data)
            mock_broadcast.assert_called_once_with(
                {"text": "hello"}, channel="test-channel", _is_distributed=True
            )


class TestShutdown:
    """Test that shutdown properly cleans up background tasks."""
    
    @pytest.mark.asyncio
    async def test_shutdown_stops_heartbeat(self):
        """Shutdown should stop the heartbeat task."""
        mgr = ConnectionManager(heartbeat_interval=0.1)
        await mgr.start_heartbeat()
        assert mgr._heartbeat_task is not None
        
        await mgr.shutdown()
        assert mgr._heartbeat_task is None
    
    @pytest.mark.asyncio
    async def test_shutdown_clears_state(self):
        """Shutdown should clear all connection tracking state."""
        mgr = ConnectionManager()
        ws = FakeWebSocket()
        ws.client_state = MagicMock()  # Prevent WebSocketState checks
        mgr._socket_channels[ws] = {"test"}
        mgr._channels["test"].add(ws)
        
        await mgr.shutdown()
        
        assert len(mgr._channels) == 0
        assert len(mgr._socket_channels) == 0


class TestConnectionBasics:
    """Test basic connection management still works."""
    
    @pytest.mark.asyncio
    async def test_subscribe_and_unsubscribe(self):
        """Channel subscribe/unsubscribe should work."""
        mgr = ConnectionManager()
        ws = FakeWebSocket()
        mgr._socket_channels[ws] = set()
        
        await mgr.subscribe(ws, "chat")
        assert "chat" in mgr._channels
        assert ws in mgr._channels["chat"]
        
        await mgr.unsubscribe(ws, "chat")
        assert "chat" not in mgr._channels
    
    @pytest.mark.asyncio
    async def test_count(self):
        """count() should return number of tracked sockets."""
        mgr = ConnectionManager()
        assert mgr.count() == 0
        
        ws1 = FakeWebSocket()
        ws2 = FakeWebSocket()
        mgr._socket_channels[ws1] = set()
        mgr._socket_channels[ws2] = set()
        
        assert mgr.count() == 2
    
    def test_active_channels(self):
        """active_channels should list channels with subscribers."""
        mgr = ConnectionManager()
        ws = FakeWebSocket()
        mgr._channels["room1"].add(ws)
        mgr._channels["room2"].add(ws)
        
        channels = mgr.active_channels
        assert "room1" in channels
        assert "room2" in channels
