import asyncio
import pytest
import logging
from datetime import datetime
from eden import Eden, Depends
from eden.tasks import EdenBroker, create_broker

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("eden.tasks")

# Track task executions
task_state = {
    "execution_count": 0,
    "last_arg": None,
    "di_resolved": False,
    "retry_attempts": 0
}

def reset_state():
    task_state["execution_count"] = 0
    task_state["last_arg"] = None
    task_state["di_resolved"] = False
    task_state["retry_attempts"] = 0

@pytest.fixture
def app():
    app = Eden(debug=True)
    reset_state()
    return app

async def get_test_dep():
    return "resolved_dep"

class TestTasksAdvanced:
    @pytest.mark.asyncio
    async def test_task_di_support(self, app):
        @app.task()
        async def my_task(arg, dep=Depends(get_test_dep)):
            task_state["execution_count"] += 1
            task_state["last_arg"] = arg
            if dep == "resolved_dep":
                task_state["di_resolved"] = True

        await app.broker.startup()
        try:
            # We must wait for the result even in InMemoryBroker
            task = await my_task.kiq(arg="hello")
            await task.wait_result(timeout=2)
            
            assert task_state["execution_count"] == 1
            assert task_state["last_arg"] == "hello"
            assert task_state["di_resolved"] is True
        finally:
            await app.broker.shutdown()

    @pytest.mark.asyncio
    async def test_task_retries(self, app):
        @app.task(max_retries=2, retry_delays=[0.1, 0.1])
        async def failing_task():
            task_state["retry_attempts"] += 1
            if task_state["retry_attempts"] < 3:
                raise ValueError("Failed")
            return "success"

        await app.broker.startup()
        try:
            task = await failing_task.kiq()
            await task.wait_result(timeout=2)
            # 1 initial + 2 retries = 3 attempts total
            assert task_state["retry_attempts"] == 3
        finally:
            await app.broker.shutdown()

    @pytest.mark.asyncio
    async def test_periodic_task_cron(self, app):
        execution_log = []
        
        @app.task.every(cron="* * * * *")
        async def cron_task():
            execution_log.append(datetime.now())

        pytest.importorskip("croniter")
        from croniter import croniter
        now = datetime.now()
        it = croniter("* * * * *", now)
        next_run = it.get_next(datetime)
        assert (next_run - now).total_seconds() <= 60

    @pytest.mark.asyncio
    async def test_periodic_task_interval(self, app):
        @app.task.every(seconds=0.1)
        async def interval_task():
            task_state["execution_count"] += 1

        await app.broker.startup()
        try:
            await asyncio.sleep(0.45) # Should run ~4 times, but at least 3
            assert task_state["execution_count"] >= 3
        finally:
            await app.broker.shutdown()
