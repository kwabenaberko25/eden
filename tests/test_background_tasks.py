import pytest
import asyncio
from eden import Eden

@pytest.fixture
def app():
    app = Eden(title="Test Task App")
    return app

@pytest.mark.asyncio
async def test_task_decorator_and_defer(app):
    await app.broker.startup()
    try:
        task_ran = False
        
        @app.task
        async def my_task(value: str):
            nonlocal task_ran
            task_ran = True
            return f"Hello {value}"

        # Verify registration
        assert "my_task" in my_task.task_name
        
        # Run task through broker
        await app.task.defer(my_task, "Eden")
        
        # Give InMemoryBroker a moment to process
        await asyncio.sleep(0.1)
        
        # Since it's InMemoryBroker, it should have executed
        assert task_ran is True
    finally:
        await app.broker.shutdown()

@pytest.mark.asyncio
async def test_task_schedule(app):
    # This might be tricky to test with InMemoryBroker without a real event loop / clock control
    # but we can at least verify the call doesn't crash.
    @app.task
    async def delayed_task():
        pass
        
    # Just verify it doesn't fail
    await app.task.schedule(delayed_task, 0.1)
