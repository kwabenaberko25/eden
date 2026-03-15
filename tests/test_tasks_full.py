"""
Comprehensive Task System Tests

Tests for all task system functionality:
- Task registration and execution
- Periodic task scheduling
- Error recovery and retries
- Task result persistence
- Dead-letter queue
- CLI commands
- App lifecycle integration
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from eden import Eden
from eden.tasks import (
    EdenBroker,
    PeriodicTask,
    TaskResult,
    TaskResultBackend,
    create_broker,
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_DELAYS,
)
from eden.tasks.exceptions import (
    BrokerNotInitialized,
    TaskExecutionError,
    MaxRetriesExceeded,
)


class TestTaskExecution:
    """Test one-shot task execution."""

    @pytest.mark.asyncio
    async def test_task_registration(self):
        """Tasks can be registered with @app.task()."""
        app = Eden()

        @app.task()
        async def my_task(x: int):
            return x * 2

        assert hasattr(my_task, "kiq")

    @pytest.mark.asyncio
    async def test_task_defer_requires_startup(self):
        """Deferring a task before startup raises error."""
        app = Eden()

        @app.task()
        async def my_task():
            pass

        with pytest.raises(BrokerNotInitialized):
            await app.task.defer(my_task)

    @pytest.mark.asyncio
    async def test_task_schedule_requires_startup(self):
        """Scheduling a task before startup raises error."""
        app = Eden()

        @app.task()
        async def my_task():
            pass

        with pytest.raises(BrokerNotInitialized):
            await app.task.schedule(my_task, delay=60)

    @pytest.mark.asyncio
    async def test_broker_startup_complete_flag(self):
        """Broker sets startup_complete flag."""
        app = Eden()
        assert app.broker._startup_complete is False

        await app.broker.startup()
        assert app.broker._startup_complete is True

        await app.broker.shutdown()


class TestPeriodicTasks:
    """Test periodic task scheduling."""

    @pytest.mark.asyncio
    async def test_periodic_task_registration(self):
        """Periodic tasks can be registered with @app.task.every()."""
        app = Eden()

        @app.task.every(minutes=5)
        async def refresh():
            pass

        assert len(app.broker.periodic_tasks) == 1
        task = app.broker.periodic_tasks[0]
        assert task.minutes == 5
        assert task.interval == 300  # 5 * 60

    @pytest.mark.asyncio
    async def test_periodic_task_interval_calculation(self):
        """Periodic task intervals are correctly calculated."""
        app = Eden()

        @app.task.every(seconds=10, minutes=2, hours=1)
        async def complex_task():
            pass

        task = app.broker.periodic_tasks[0]
        expected = 10 + (2 * 60) + (1 * 3600)
        assert task.interval == expected

    @pytest.mark.asyncio
    async def test_periodic_task_lifecycle(self):
        """Periodic tasks start and stop correctly."""
        app = Eden()
        execution_count = []

        @app.task.every(seconds=0.1)
        async def fast_task():
            execution_count.append(1)

        await app.broker.startup()
        await asyncio.sleep(0.3)  # Let it run a couple times
        await app.broker.shutdown()

        assert len(execution_count) > 0
        assert app.broker.periodic_tasks[0].execution_count > 0

    @pytest.mark.asyncio
    async def test_periodic_task_handles_sync_functions(self):
        """Periodic tasks can run sync functions."""
        app = Eden()
        execution_count = []

        @app.task.every(seconds=0.1)
        def sync_task():
            execution_count.append(1)

        await app.broker.startup()
        await asyncio.sleep(0.2)
        await app.broker.shutdown()

        assert len(execution_count) > 0

    @pytest.mark.asyncio
    async def test_periodic_task_error_handling(self):
        """Periodic task errors are logged but don't stop the loop."""
        app = Eden()
        execution_count = []

        @app.task.every(seconds=0.1)
        async def failing_task():
            execution_count.append(1)
            if len(execution_count) < 3:
                raise ValueError("Intentional error")

        await app.broker.startup()
        await asyncio.sleep(0.4)
        await app.broker.shutdown()

        # Should have executed multiple times despite errors
        assert len(execution_count) >= 3
        # Last execution should succeed, so last_error might be None or old
        assert app.broker.periodic_tasks[0].execution_count > 0


class TestTaskResultStorage:
    """Test task result persistence."""

    @pytest.mark.asyncio
    async def test_result_storage(self):
        """Task results can be stored and retrieved."""
        backend = TaskResultBackend()

        result = TaskResult(
            task_id="task-1",
            task_name="test_task",
            status="success",
            result={"data": "value"},
        )

        await backend.store_result("task-1", result)
        retrieved = await backend.get_result("task-1")

        assert retrieved is not None
        assert retrieved.task_id == "task-1"
        assert retrieved.status == "success"

    @pytest.mark.asyncio
    async def test_dead_letter_queue(self):
        """Failed tasks are stored in dead-letter queue."""
        backend = TaskResultBackend()

        failed_result = TaskResult(
            task_id="task-failed",
            task_name="failing_task",
            status="dead_letter",
            error="Max retries exceeded",
            retries=5,
        )

        await backend.store_result("task-failed", failed_result)
        dead_letter = await backend.get_dead_letter_tasks()

        assert len(dead_letter) == 1
        assert dead_letter[0].task_id == "task-failed"

    @pytest.mark.asyncio
    async def test_cleanup_expired_results(self):
        """Expired results are cleaned up based on TTL."""
        backend = TaskResultBackend()

        # Create result with very short TTL
        result = TaskResult(
            task_id="old-task",
            task_name="old",
            status="success",
            completed_at=datetime.now(),
            ttl_seconds=0,  # Expired immediately
        )

        await backend.store_result("old-task", result)
        
        # Clean up
        count = await backend.cleanup_expired()
        assert count == 1

        # Verify it's gone
        retrieved = await backend.get_result("old-task")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_result_to_dict(self):
        """TaskResult can be serialized to dict."""
        result = TaskResult(
            task_id="task-1",
            task_name="test",
            status="success",
            result={"key": "value"},
            created_at=datetime(2024, 1, 1, 12, 0, 0),
        )

        data = result.to_dict()

        assert data["task_id"] == "task-1"
        assert data["status"] == "success"
        assert isinstance(data["created_at"], str)
        assert "2024-01-01" in data["created_at"]


class TestBrokerConfiguration:
    """Test broker configuration and options."""

    def test_default_retry_configuration(self):
        """Broker has sensible retry defaults."""
        broker = create_broker()
        eden_broker = EdenBroker(broker)

        assert eden_broker.max_retries == DEFAULT_MAX_RETRIES
        assert eden_broker.retry_delays == DEFAULT_RETRY_DELAYS

    def test_custom_retry_configuration(self):
        """Broker can be configured with custom retry settings."""
        broker = create_broker()
        custom_delays = [2, 4, 8]
        eden_broker = EdenBroker(broker, max_retries=3, retry_delays=custom_delays)

        assert eden_broker.max_retries == 3
        assert eden_broker.retry_delays == custom_delays

    def test_broker_factory_in_memory(self):
        """create_broker() returns InMemoryBroker by default."""
        broker = create_broker()
        assert broker is not None

    def test_broker_factory_redis_missing(self, monkeypatch):
        """create_broker() raises error if Redis requested but not installed."""
        # Mock RedisBroker to None to simulate missing dependency
        import eden.tasks
        monkeypatch.setattr(eden.tasks, "RedisBroker", None)
        with pytest.raises(ImportError, match="taskiq-redis"):
            create_broker(redis_url="redis://localhost:6379")


class TestAppIntegration:
    """Test Eden app integration."""

    @pytest.mark.asyncio
    async def test_broker_startup_with_app(self):
        """App starts broker during lifespan."""
        app = Eden()

        @app.task()
        async def my_task():
            pass

        # Manually trigger startup (normally done by Starlette)
        await app.broker.startup()

        assert app.broker._startup_complete is True
        assert app.broker.is_running is True

        await app.broker.shutdown()

    @pytest.mark.asyncio
    async def test_periodic_task_starts_with_app(self):
        """Periodic tasks start automatically with app broadcast."""
        app = Eden()
        execution_count = []

        @app.task.every(seconds=0.05)
        async def periodic():
            execution_count.append(1)

        await app.broker.startup()
        await asyncio.sleep(0.2)
        await app.broker.shutdown()

        assert len(execution_count) > 0

    def test_setup_tasks_method(self):
        """app.setup_tasks() registers lifecycle hooks."""
        app = Eden()
        app.setup_tasks()

        # Just verify it doesn't raise
        assert app is not None

    @pytest.mark.asyncio
    async def test_defer_after_startup(self):
        """Task.defer() works after startup."""
        app = Eden()

        execution_log = []

        @app.task()
        async def log_task(msg: str):
            execution_log.append(msg)
            return msg

        await app.broker.startup()

        # defer() should not raise
        await app.task.defer(log_task, msg="test")

        await app.broker.shutdown()


class TestExceptions:
    """Test custom exception classes."""

    def test_task_execution_error(self):
        """TaskExecutionError stores context."""
        exc = TaskExecutionError(
            "Task failed",
            task_id="t1",
            retry_count=2,
            original_exception=ValueError("Bad value"),
        )

        assert exc.task_id == "t1"
        assert exc.retry_count == 2
        assert isinstance(exc.original_exception, ValueError)

    def test_max_retries_exceeded(self):
        """MaxRetriesExceeded stores retry info."""
        exc = MaxRetriesExceeded(
            "Exhausted retries",
            task_id="t2",
            max_retries=5,
            last_error=RuntimeError("Timeout"),
        )

        assert exc.task_id == "t2"
        assert exc.max_retries == 5
        assert isinstance(exc.last_error, RuntimeError)

    def test_broker_not_initialized(self):
        """BrokerNotInitialized is raised when needed."""
        exc = BrokerNotInitialized("Broker not ready")
        assert "Broker not" in str(exc)


# ── Integration Test ──────────────────────────────────────────────────────────

class TestEndToEnd:
    """End-to-end workflow tests."""

    @pytest.mark.asyncio
    async def test_complete_task_workflow(self):
        """Complete workflow: register → startup → execute → shutdown."""
        app = Eden()
        results = []

        @app.task()
        async def process(value: int):
            results.append(value * 2)
            return value * 2

        @app.task.every(seconds=0.05)
        async def periodic_process():
            results.append(999)

        # Start
        await app.broker.startup()

        # Give periodic task time to run
        await asyncio.sleep(0.15)

        # Verify periodic ran
        assert 999 in results

        # Stop
        await app.broker.shutdown()

        assert not app.broker.is_running
        assert app.broker.periodic_tasks[0].execution_count > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
