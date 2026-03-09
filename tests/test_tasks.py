import pytest
import asyncio
from eden import Eden

@pytest.mark.asyncio
async def test_task_registration_and_trigger():
    app = Eden()
    
    # Store evidence that task ran
    task_run_data = []

    @app.task()
    async def add_numbers(a: int, b: int):
        task_run_data.append(a + b)
        return a + b

    # Ensure it is a taskiq task
    assert hasattr(add_numbers, "kiq")
    
    # In-memory broker needs to be started
    await app.broker.startup()
    
    # Trigger the task
    # Note: .kiq() sends it to broker
    await add_numbers.kiq(10, 20)
    
    # Since it's InMemoryBroker, it should run immediately (usually)
    # But taskiq handles it in a loop
    await asyncio.sleep(0.1)
    
    assert 30 in task_run_data
    
    await app.broker.shutdown()

@pytest.mark.asyncio
async def test_app_lifespan_starts_broker():
    from unittest.mock import AsyncMock
    app = Eden()
    
    # Mock the broker's startup and shutdown
    app.broker.startup = AsyncMock()
    app.broker.shutdown = AsyncMock()
    
    # Simulate lifespan manually using Starlette's TestClient
    from starlette.testclient import TestClient
    
    @app.get("/")
    async def index():
        return {"ok": True}
        
    with TestClient(app) as client:
        # Starlette's TestClient calls lifespan events
        assert app.broker.startup.called is True
    
    # After exit, broker should be shutdown
    assert app.broker.shutdown.called is True

def test_periodic_task_registration():
    app = Eden()
    
    @app.task.every(minutes=5)
    async def my_periodic_task():
        pass
        
    assert len(app.broker.periodic_tasks) == 1
    ptask = app.broker.periodic_tasks[0]
    assert ptask.task == my_periodic_task
    assert ptask.minutes == 5
    assert hasattr(my_periodic_task, "kiq")
