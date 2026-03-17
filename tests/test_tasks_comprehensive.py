import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from eden import Eden
from eden.tasks import TaskResult, EdenBroker
from eden.tasks.exceptions import MaxRetriesExceeded

@pytest.mark.asyncio
async def test_task_result_recording_success():
    app = Eden()
    
    @app.task()
    async def my_success_task(x: int):
        return x * 2
    
    await app.broker.startup()
    
    # Trigger task
    await my_success_task.kiq(21)
    
    # Give it time to run in InMemoryBroker
    await asyncio.sleep(0.1)
    
    # Check results
    results = await app.broker._result_backend.get_all_results()
    assert len(results) >= 1
    # Find our task result
    task_res = next(r for r in results if r.task_name == "my_success_task")
    assert task_res.status == "success"
    assert task_res.result == 42
    assert task_res.completed_at is not None
    assert task_res.started_at is not None
    
    await app.broker.shutdown()

@pytest.mark.asyncio
async def test_task_retries_and_dead_letter():
    app = Eden()
    
    # Track attempts
    attempts = 0
    
    @app.task(retries=2, delays=[0, 0])
    async def failing_task():
        nonlocal attempts
        attempts += 1
        raise ValueError("Boom")
    
    await app.broker.startup()
    
    # Trigger task
    await failing_task.kiq()
    
    # Give InMemoryBroker plenty of time to retry 
    await asyncio.sleep(1.0)
    
    # Check results in backend
    all_results = await app.broker._result_backend.get_all_results()
    for r in all_results:
        print(f"DEBUG RESULT: {r.task_name} status={r.status} attempt={r.retries} id={r.task_id}")
    
    # Check attempts
    assert attempts == 3, f"Expected 3 attempts, got {attempts}. Last status: {all_results[0].status if all_results else 'None'}"
    
    # Check results for dead_letter
    dead_letters = await app.broker._result_backend.get_dead_letter_tasks()
    assert len(dead_letters) >= 1
    res = next(r for r in dead_letters if r.task_name == "failing_task")
    assert res.status == "dead_letter"
    assert "Boom" in res.error
    assert res.retries == 2
    
    await app.broker.shutdown()

@pytest.mark.asyncio
async def test_dependency_injection_in_task():
    app = Eden()
    
    class MockService:
        def getValue(self): return "injected"
    
    @app.task()
    async def injected_task(service: MockService):
        return service.getValue()
    
    # Inject MockService into app state or similar for DependencyResolver
    # Actually, DependencyResolver needs to be able to find it.
    # In Eden, we usually register dependencies or hope they are findable.
    
    # For this test, let's just mock the resolver or the service injection.
    # Or better, use a real Depends()
    from eden.dependencies import Depends
    
    def get_val():
        return "from-depends"
        
    @app.task()
    async def depends_task(val: str = Depends(get_val)):
        return val

    await app.broker.startup()
    await depends_task.kiq()
    await asyncio.sleep(0.1)
    
    results = await app.broker._result_backend.get_all_results()
    res = next(r for r in results if r.task_name == "depends_task")
    assert res.result == "from-depends"
    
    await app.broker.shutdown()

@pytest.mark.asyncio
async def test_periodic_task_history():
    app = Eden()
    
    run_count = 0
    @app.task.every(seconds=0.1)
    async def fast_periodic():
        nonlocal run_count
        run_count += 1
        
    await app.broker.startup()
    
    # Wait for at least 2 runs
    await asyncio.sleep(0.35)
    
    await app.broker.shutdown()
    
    assert run_count >= 2
    
    # Check results recorded for periodic task
    results = await app.broker._result_backend.get_all_results()
    periodic_results = [r for r in results if r.task_name == "fast_periodic"]
    assert len(periodic_results) >= 2
    assert all(r.status == "success" for r in periodic_results)

@pytest.mark.asyncio
async def test_result_backend_cleanup():
    app = Eden()
    backend = app.broker._result_backend
    
    # Store an expired result
    old_res = TaskResult(
        task_id="old",
        task_name="test",
        status="success",
        completed_at=datetime.now() - timedelta(days=10),
        ttl_seconds=3600 # 1 hour
    )
    await backend.store_result("old", old_res)
    
    # Store a fresh result
    new_res = TaskResult(
        task_id="new",
        task_name="test",
        status="success",
        completed_at=datetime.now(),
        ttl_seconds=3600
    )
    await backend.store_result("new", new_res)
    
    cleaned = await backend.cleanup_expired()
    assert cleaned == 1
    assert await backend.get_result("old") is None
    assert await backend.get_result("new") is not None
