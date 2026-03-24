import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from starlette.websockets import WebSocket, WebSocketState
from eden.websocket.manager import ConnectionManager
from eden.core.metrics import MetricsRegistry
from eden.core.idempotency import IdempotencyManager, with_idempotency

@pytest.mark.asyncio
async def test_websocket_origin_validation():
    # Manager with origin whitelist
    manager = ConnectionManager(allowed_origins=[r"https://eden\.dev"])
    
    # Mock WebSocket with blocked origin
    mock_ws = AsyncMock(spec=WebSocket)
    mock_ws.headers = {"origin": "https://evil.com"}
    mock_ws.client_state = WebSocketState.CONNECTING
    
    await manager.connect(mock_ws)
    mock_ws.close.assert_called_with(code=4003)

    # Mock WebSocket with allowed origin
    mock_ws_allowed = AsyncMock(spec=WebSocket)
    mock_ws_allowed.headers = {"origin": "https://eden.dev"}
    mock_ws_allowed.client_state = WebSocketState.CONNECTING
    
    await manager.connect(mock_ws_allowed)
    mock_ws_allowed.accept.assert_called_once()

@pytest.mark.asyncio
async def test_websocket_csrf_validation():
    # Manager requiring CSRF
    manager = ConnectionManager(require_csrf=True)
    
    # Mock WebSocket with missing/invalid CSRF
    mock_ws = AsyncMock(spec=WebSocket)
    mock_ws.scope = {"session": {"eden_csrf_token": "secret"}}
    mock_ws.query_params = {"csrf_token": "wrong"}
    mock_ws.headers = {}
    
    await manager.connect(mock_ws)
    mock_ws.close.assert_called_with(code=4403)

    # Mock WebSocket with valid CSRF
    mock_ws_valid = AsyncMock(spec=WebSocket)
    mock_ws_valid.scope = {"session": {"eden_csrf_token": "secret"}}
    mock_ws_valid.query_params = {"csrf_token": "secret"}
    mock_ws_valid.headers = {}
    mock_ws_valid.client_state = WebSocketState.CONNECTING
    
    await manager.connect(mock_ws_valid)
    mock_ws_valid.accept.assert_called_once()

def test_metrics_collection():
    reg = MetricsRegistry()
    reg.increment("test_counter", 1)
    reg.set_gauge("test_gauge", 42)
    reg.observe("test_latency", 0.5)
    reg.observe("test_latency", 0.7)
    
    all_metrics = reg.get_all_metrics()
    assert all_metrics["counters"]["test_counter"] == 1
    assert all_metrics["gauges"]["test_gauge"] == 42
    assert all_metrics["histograms"]["test_latency"]["count"] == 2
    assert all_metrics["histograms"]["test_latency"]["avg"] == 0.6

@pytest.mark.asyncio
async def test_idempotency():
    backend = AsyncMock()
    backend.get.return_value = None
    backend.acquire_lock.return_value = True
    
    manager = IdempotencyManager(backend)
    
    call_count = 0
    async def my_op(val):
        nonlocal call_count
        call_count += 1
        return {"id": val}

    # First call
    res1 = await with_idempotency(manager, "key1", my_op, 123)
    assert res1 == {"id": 123}
    assert call_count == 1
    
    # Mock result in backend for second call
    backend.get.return_value = '{"id": 123}'
    
    # Second call (should be idempotent)
    res2 = await with_idempotency(manager, "key1", my_op, 123)
    assert res2 == {"id": 123}
    assert call_count == 1 # Still 1
