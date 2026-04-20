import pytest
import asyncio
import uuid
import logging
from unittest.mock import AsyncMock, MagicMock, patch, call
from starlette.testclient import TestClient
from starlette.websockets import WebSocketState
from eden.app import Eden
from eden.tasks import EdenBroker, create_broker, TaskResult, TaskResultBackend
from eden.websocket.manager import ConnectionManager
from eden.middleware.correlation import CorrelationIdMiddleware
from eden.context import set_request_id, reset_request_id

@pytest.fixture
def app():
    app = Eden(title="ReliabilityTest")
    app.enable_health_checks()
    return app

class TestPhase3Reliability:
    
    @pytest.mark.asyncio
    async def test_correlation_id_propagation(self, app):
        """Test that correlation ID is generated and propagated to context."""
        from eden.context import context_manager
        
        middleware = CorrelationIdMiddleware(AsyncMock())
        scope = {"type": "http", "headers": []}
        receive = AsyncMock()
        send = AsyncMock()
        
        # Test generation
        await middleware(scope, receive, send)
        assert "eden_request_id" in scope
        req_id = scope["eden_request_id"]
        assert len(req_id) > 0
        
        # Test propagation from headers
        scope["headers"] = [(b"x-request-id", b"test-correlation-id")]
        await middleware(scope, receive, send)
        assert scope["eden_request_id"] == "test-correlation-id"

    @pytest.mark.asyncio
    async def test_task_retry_logic(self, app):
        """Test task retry logic with exponential backoff."""
        from eden.tasks import EdenBroker
        from eden.tasks import TaskResultBackend
        
        mock_result_backend = AsyncMock(spec=TaskResultBackend)
        broker = EdenBroker(create_broker(None))
        broker._result_backend = mock_result_backend
        
        # Define a failing task
        attempts = 0
        async def failing_task():
            nonlocal attempts
            attempts += 1
            raise ValueError("Intentional failure")

        # Defining and getting function to test
        handler = broker._wrap_task_function(failing_task, 2, [1.0], exponential_backoff=True)
        
        with patch("asyncio.sleep", AsyncMock()) as mock_sleep:
            with pytest.raises(Exception):
                await handler()
            
            # Verify exponential backoff: 1.0, 2.0
            assert mock_sleep.call_count == 2
            mock_sleep.assert_has_calls([call(1.0), call(2.0)])
        
        # Initial attempt + 2 retries = 3
        assert attempts == 3
        
        # Check that dead_letter was recorded
        calls = mock_result_backend.store_result.call_args_list
        # Should have status="failed" for intermediate and "dead_letter" for final
        statuses = [call.args[1].status for call in calls]
        assert "failed" in statuses
        assert "dead_letter" in statuses
        
        # Verify backoff was exponential
        # asyncio.sleep(1.0) then asyncio.sleep(2.0)
        # Assuming our logic uses (2 ** (attempt-1)) starting at attempt 1
        # attempt 1 delay = 1 * 2^0 = 1
        # attempt 2 delay = 1 * 2^1 = 2
        # No, wait. Attempt counts starts at 1?
        # Let's check eden/tasks/__init__.py: 
        # attempt starts at 0. First failure: attempt becomes 1.
        # idx = min(1-1, len(delays)-1) = 0.
        # delay = delays[0] * (2 ** (1-1)) = 1 * 1 = 1.
        # Second failure: attempt becomes 2. 
        # idx = min(2-1, len(delays)-1) = 1.
        # delay = delays[1] * (2 ** (2-1)) = 1 * 2 = 2.
        # Correct.

    @pytest.mark.asyncio
    async def test_websocket_graceful_shutdown(self):
        """Test that all websockets are closed on shutdown."""
        manager = ConnectionManager()
        mock_ws = AsyncMock()
        mock_ws.client_state = WebSocketState.CONNECTED
        
        # Simulate connection
        manager._socket_channels[mock_ws] = {"test"}
        
        await manager.shutdown()
        
        mock_ws.close.assert_called_once_with(code=1001)
        assert len(manager._socket_channels) == 0

    @pytest.mark.asyncio
    async def test_deep_health_checks(self, app):
        """Test health check infrastructure probes."""
        # 1. Mock DB engines
        from eden.db import Model
        class MockConnection:
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
            async def execute(self, *args): pass

        mock_engine = MagicMock()
        mock_engine.connect.return_value = MockConnection()
        
        mock_db = MagicMock()
        mock_db.engine = mock_engine
        Model._db = mock_db
        
        # 2. Mock Distributed Backend
        mock_backend = AsyncMock()
        app.distributed_backend = mock_backend
        
        # We need to mock metrics because app.metrics will be used
        app.metrics = MagicMock()
        
        # Run check
        client = TestClient(app)
        
        response = client.get("/ready")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["probes"]["db:default"] == "ok"
        assert data["probes"]["distributed_backend"] == "ok"

    @pytest.mark.asyncio
    async def test_task_correlation_id(self, app):
        """Test that tasks inherit correlation ID if provided in context."""
        from eden.tasks import EdenBroker
        broker = EdenBroker(create_broker(None))
        broker.app = app
        
        async def tracked_task():
            from eden.context import context_manager
            return context_manager.get_request_id()

        # Defining and getting function to test
        # We wrap it manually to pass mock_tiq_context
        handler = broker._wrap_task_function(tracked_task, 0, [])
        
        mock_tiq_context = MagicMock()
        mock_tiq_context.labels = {"correlation_id": "task-inherited-id"}
        
        # We need to ensure DependencyResolver doesn't fail if app is missing some parts
        res2 = await handler(context=mock_tiq_context)
        assert res2 == "task-inherited-id"
