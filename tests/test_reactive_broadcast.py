
import pytest
import uuid
import asyncio
from unittest.mock import AsyncMock, patch
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Uuid

from eden.db.base import Model, reactive
from eden.db.listeners import _trigger_broadcast
from eden.context import context_manager

# Define test models
@reactive
class ReactiveTask(Model):
    __tablename__ = "reactive_tasks_test"
    name: Mapped[str] = mapped_column(String)

@reactive
class TenantIsolatedTask(Model):
    __tablename__ = "tenant_tasks_test"
    __eden_tenant_isolated__ = True
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    name: Mapped[str] = mapped_column(String)

@pytest.mark.asyncio
async def test_reactive_channels_standard():
    """Verify that a standard reactive model broadcasts to non-prefixed channels."""
    task_id = uuid.uuid4()
    task = ReactiveTask(id=task_id, name="Test Task")
    
    # Mock connection_manager.broadcast
    # We patch inside the async loop to ensure it's picked up by the background task
    with patch("eden.websocket.connection_manager.broadcast", new_callable=AsyncMock) as mock_broadcast:
        _trigger_broadcast(None, None, task, "updated")
        
        # Wait a bit for the background task (asyncio.create_task) to execute
        await asyncio.sleep(0.1)
        
        # Verify calls
        assert mock_broadcast.call_count == 2
        channels = [call.kwargs["channel"] for call in mock_broadcast.call_args_list]
        assert "reactive_tasks_test" in channels
        assert f"reactive_tasks_test:{task_id}" in channels
        
        # Verify event data
        msg = mock_broadcast.call_args_list[0].args[0]
        assert msg["event"] == "updated"
        assert msg["data"]["name"] == "Test Task"

@pytest.mark.asyncio
async def test_reactive_channels_tenant_isolated():
    """Verify that a tenant-isolated model broadcasts to tenant-prefixed channels."""
    tenant_id = uuid.uuid4()
    task_id = uuid.uuid4()
    task = TenantIsolatedTask(id=task_id, tenant_id=tenant_id, name="Tenant Task")
    
    with patch("eden.websocket.connection_manager.broadcast", new_callable=AsyncMock) as mock_broadcast:
        # Set tenant context
        context_manager.set_tenant(str(tenant_id))
        
        _trigger_broadcast(None, None, task, "created")
        
        # Wait for background task
        await asyncio.sleep(0.1)
        
        # Verify prefixed channels
        assert mock_broadcast.call_count == 2
        channels = [call.kwargs["channel"] for call in mock_broadcast.call_args_list]
        assert f"tenant:{tenant_id}:tenant_tasks_test" in channels
        assert f"tenant:{tenant_id}:tenant_tasks_test:{task_id}" in channels
        
        # Verify event type
        msg = mock_broadcast.call_args_list[0].args[0]
        assert msg["event"] == "created"

@pytest.mark.asyncio
async def test_context_persistence_in_broadcast():
    """Verify that tenant context is preserved in the background broadcast task."""
    tenant_id = uuid.uuid4()
    task = TenantIsolatedTask(id=uuid.uuid4(), tenant_id=tenant_id, name="Context Task")
    
    # This specifically tests the contextvars.copy_context() logic
    async def mock_broadcast_impl(msg, channel=None):
        from eden.context import get_tenant_id
        # Inside the background task, the tenant ID should still be accessible
        # even if it was cleared in the main thread (simulated here implicitly)
        assert get_tenant_id() == str(tenant_id)
        return None

    with patch("eden.websocket.connection_manager.broadcast", side_effect=mock_broadcast_impl) as mock_broadcast:
        context_manager.set_tenant(str(tenant_id))
        
        _trigger_broadcast(None, None, task, "updated")
        
        # Clear context immediately in the "main thread"
        context_manager.set_tenant(None)
        
        # Wait for background task
        await asyncio.sleep(0.1)
        
        assert mock_broadcast.call_count == 2
