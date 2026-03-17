import pytest
import time
import asyncio
from unittest.mock import MagicMock
from eden.telemetry import TelemetryData, start_telemetry, get_telemetry, reset_telemetry, record_query, record_template_render

@pytest.mark.asyncio
async def test_telemetry_duration_and_counts():
    """Verify that telemetry accurately counts queries and tracks duration."""
    token = start_telemetry()
    data = get_telemetry()
    
    assert data is not None
    assert data.db_queries == 0
    
    # Record some queries
    record_query(10.5)
    record_query(5.5)
    
    # Record template render
    record_template_render(100.0)
    
    assert data.db_queries == 2
    assert data.db_time_ms == 16.0
    assert data.template_time_ms == 100.0
    
    # Allow some time to pass
    await asyncio.sleep(0.01)
    
    assert data.total_duration_ms >= 10.0
    
    reset_telemetry(token)
    assert get_telemetry() is None

@pytest.mark.asyncio
async def test_memory_tracking_present():
    """Verify that memory tracking properties exist and return a number."""
    token = start_telemetry()
    data = get_telemetry()
    
    # Even if psutil is missing, it should return 0.0, not crash
    delta = data.memory_delta_mb
    assert isinstance(delta, float)
    
    reset_telemetry(token)

@pytest.mark.asyncio
async def test_telemetry_header_injection():
    """Verify that PerformanceTelemetryMiddleware injects correctly formatted headers."""
    from eden.middleware import PerformanceTelemetryMiddleware
    
    async def app(scope, receive, send):
        # Record some metrics during 'request'
        record_query(50.0)
        record_template_render(20.0)
        
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", b"text/plain")]
        })
        await send({
            "type": "http.response.body",
            "body": b"Hello"
        })

    middleware = PerformanceTelemetryMiddleware(app)
    
    scope = {"type": "http", "method": "GET", "path": "/"}
    
    messages = []
    async def mock_send(msg):
        messages.append(msg)
    
    # We need to manually simulate start/reset because middleware calls it
    # and we want to check the messages.
    await middleware(scope, None, mock_send)
    
    # Check response start message for headers
    response_start = next(m for m in messages if m["type"] == "http.response.start")
    headers = dict(response_start["headers"])
    
    assert b"server-timing" in headers
    timing_val = headers[b"server-timing"].decode()
    assert "db;dur=50.00" in timing_val
    assert "tpl;dur=20.00" in timing_val
    assert "total;dur=" in timing_val
    assert "mem;dur=" in timing_val
