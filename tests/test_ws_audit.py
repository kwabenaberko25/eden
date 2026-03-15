import asyncio
import sys
import os
import json
from unittest.mock import MagicMock, AsyncMock

# Add current directory to path
sys.path.append(os.getcwd())

from starlette.websockets import WebSocketState
from eden.websocket import (
    WebSocketRouter, 
    ConnectionManager, 
    connection_manager
)

async def test_websocket_manager():
    print("Testing Unified ConnectionManager...")
    manager = ConnectionManager()
    
    # Mock WebSocket
    mock_ws = AsyncMock()
    mock_ws.client_state = WebSocketState.CONNECTED # Important!
    
    # Test Connect
    await manager.connect(mock_ws, user_id="user_123")
    
    # Test Subscribe/Broadcast
    await manager.subscribe(mock_ws, "test_channel")
    assert "test_channel" in manager.active_channels
    
    # Broadcast to channel
    await manager.broadcast({"msg": "hello"}, channel="test_channel")
    mock_ws.send_json.assert_awaited_with({"msg": "hello"})
    
    # Send to specific user
    mock_ws.send_json.reset_mock()
    await manager.send_to_user("user_123", {"msg": "private"})
    mock_ws.send_json.assert_awaited_with({"msg": "private"})
    
    # Test Disconnect
    await manager.disconnect(mock_ws)
    assert mock_ws not in manager._socket_channels
    assert "test_channel" not in manager.active_channels
    
    print("✓ ConnectionManager tests passed")

async def test_websocket_router():
    print("\nTesting WebSocketRouter...")
    router = WebSocketRouter(prefix="/ws")
    
    message_received = False
    @router.on("chat")
    async def handle_chat(ws, data, manager):
        nonlocal message_received
        message_received = True
        assert data == {"text": "hi"}
        await ws.send_json({"reply": "hey"})

    # Setup mock app
    app = MagicMock()
    app._ws_routes = []
    
    # Mount
    router.mount(app)
    assert len(app._ws_routes) == 1
    
    # Simulate hitting the endpoint
    route = app._ws_routes[0]
    
    mock_ws = AsyncMock()
    mock_ws.path_params = {"channel": "my_room"}
    mock_ws.client_state = WebSocketState.CONNECTED
    
    # 1. Connect (simulated manually since we are just testing the logic flow)
    await router.manager.connect(mock_ws)
    await router.manager.subscribe(mock_ws, "my_room")
    
    # 2. Trigger handler directly for test
    handler = router._handlers.get("chat")
    await handler(mock_ws, {"text": "hi"}, router.manager)
    
    assert message_received
    mock_ws.send_json.assert_awaited_with({"reply": "hey"})
    
    print("✓ WebSocketRouter tests passed")

if __name__ == "__main__":
    async def main():
        try:
            await test_websocket_manager()
            await test_websocket_router()
            print("\n✨ ALL WEBSOCKET AUDIT TESTS PASSED ✨")
        except Exception as e:
            print(f"\n❌ TEST FAILED: {e}")
            import traceback
            traceback.print_exc()

    asyncio.run(main())
