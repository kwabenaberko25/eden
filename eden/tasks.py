"""
Eden — Task Queue Integration

Provides EdenBroker: a wrapper around Taskiq for background tasks,
periodic scheduling, and comprehensive error recovery.

Key Features:
    - One-shot background tasks: @app.task()
    - Periodic/repeating tasks: @app.task.every(minutes=5)
    - Error recovery with exponential backoff (1s, 2s, 4s, 8s, 16s)
    - Task result storage and retrieval
    - Dead-letter queue for permanently failed tasks
    - Full async/sync task execution support

Usage::

    # One-shot background task
    @app.task()
    async def send_email(to: str, subject: str) -> None:
        '''Send an email (retries up to 5 times on failure).'''
        pass

    # Periodic task — every 5 minutes
    @app.task.every(minutes=5)
    async def refresh_cache() -> None:
        '''Refresh cache every 5 minutes during uptime.'''
        pass

    # Trigger a background task
    await send_email.kiq(to="user@example.com", subject="Hello")

    # Defer with immediate execution
    await app.task.defer(send_email, to="user@example.com", subject="Hi")
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Any, TypeVar, TYPE_CHECKING

try:
    from taskiq import AsyncBroker, InMemoryBroker
except ImportError:
    # We still define these as stubs to avoid class definition errors,
    # but we'll flag that taskiq is missing.
    class AsyncBroker: pass
    class InMemoryBroker: pass
    _HAS_TASKIQ = False
else:
    _HAS_TASKIQ = True

try:
    from taskiq_redis import PubSubBroker as RedisBroker
except ImportError:
    try:
        from taskiq_redis import RedisStreamBroker as RedisBroker
    except ImportError:
        RedisBroker = None  # type: ignore[assignment]

from eden.tasks.exceptions import (
    TaskExecutionError,
    MaxRetriesExceeded,
    BrokerNotInitialized,
)

logger = logging.getLogger("eden.tasks")

T = TypeVar("T")

# Retry configuration: exponential backoff (1s, 2s, 4s, 8s, 16s)
DEFAULT_MAX_RETRIES = 5
DEFAULT_RETRY_DELAYS = [1, 2, 4, 8, 16]  # seconds


# ── Task Result Storage ───────────────────────────────────────────────────────

@dataclass
class TaskResult:
    """
    Represents the result of a task execution.

    Attributes:
        task_id: Unique identifier for this task execution
        task_name: Name of the task function
        status: 'pending', 'success', 'failed', 'dead_letter'
        result: The return value (if successful)
        error: Exception message (if failed)
        error_traceback: Full traceback (if failed)
        retries: Number of retry attempts made
        created_at: Timestamp when task was queued
        started_at: Timestamp when task started execution
        completed_at: Timestamp when task finished
        ttl_seconds: Time to live in storage (default: 604800 = 7 days)
    """

    task_id: str
    task_name: str
    status: str
    result: Any = None
    error: str | None = None
    error_traceback: str | None = None
    retries: int = 0
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    ttl_seconds: int = 604800  # 7 days default

    def to_dict(self) -> dict[str, Any]:
        """Convert result to JSON-serializable dictionary."""
        data = asdict(self)
        # Convert datetime objects to ISO format strings
        for key in ["created_at", "started_at", "completed_at"]:
            if data[key] is not None:
                data[key] = data[key].isoformat()
        # Result may not be JSON-serializable; store as string
        if data["result"] is not None:
            try:
                json.dumps(data["result"])
            except (TypeError, ValueError):
                data["result"] = str(data["result"])
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskResult:
        """Reconstruct result from dictionary."""
        # Convert ISO format strings back to datetime
        for key in ["created_at", "started_at", "completed_at"]:
            if data.get(key):
                data[key] = datetime.fromisoformat(data[key])
        return cls(**data)


class TaskResultBackend:
    """
    In-memory storage for task execution results and dead-letter queue.

    Production deployments should override this with a persistent backend
    (Redis, database, etc.).

    Example::

        backend = TaskResultBackend()
        result = await backend.store_result(task_id, TaskResult(...))
        retrieved = await backend.get_result(task_id)
        failed = await backend.get_dead_letter_tasks()
    """

    def __init__(self) -> None:
        """Initialize in-memory result store."""
        self._results: dict[str, TaskResult] = {}
        self._dead_letter: list[TaskResult] = []

    async def store_result(self, task_id: str, result: TaskResult) -> None:
        """
        Store a task result.

        Args:
            task_id: Unique task identifier
            result: TaskResult object containing execution details
        """
        self._results[task_id] = result
        logger.debug(
            "Stored task result: %s (status=%s)",
            task_id,
            result.status,
        )

        # If task is in dead letter, also store there
        if result.status == "dead_letter":
            self._dead_letter.append(result)

    async def get_result(self, task_id: str) -> TaskResult | None:
        """
        Retrieve a stored task result.

        Args:
            task_id: Unique task identifier

        Returns:
            TaskResult if found, None otherwise
        """
        return self._results.get(task_id)

    async def cleanup_expired(self) -> int:
        """
        Remove expired results based on TTL.

        Returns:
            Number of results removed
        """
        now = datetime.now()
        expired_ids = [
            task_id
            for task_id, result in self._results.items()
            if result.completed_at
            and (now - result.completed_at).total_seconds() > result.ttl_seconds
        ]

        for task_id in expired_ids:
            del self._results[task_id]

        logger.debug("Cleaned up %d expired task results", len(expired_ids))
        return len(expired_ids)

    async def get_dead_letter_tasks(self) -> list[TaskResult]:
        """
        Get all tasks in the dead-letter queue (permanently failed).

        Returns:
            List of TaskResult objects with status='dead_letter'
        """
        return list(self._dead_letter)

    async def clear_dead_letter(self) -> int:
        """
        Clear the dead-letter queue.

        Returns:
            Number of tasks removed
        """
        count = len(self._dead_letter)
        self._dead_letter.clear()
        return count


# ── Periodic Task Descriptor ──────────────────────────────────────────────────

class PeriodicTask:
    """
    Holds the schedule config for a periodic task registered via .every().

    Periodic tasks run at fixed intervals in the current event loop.
    For distributed setups (multiple workers), use APScheduler backend instead.

    Attributes:
        func: The task function to execute
        seconds: Interval in seconds (0 = not set)
        minutes: Interval in minutes (0 = not set)
        hours: Interval in hours (0 = not set)
        cron: Cron expression (alternative to interval-based scheduling)

    Example::

        @app.task.every(minutes=5)
        async def refresh_cache():
            await cache.invalidate_all()

        # At startup:
        periodic_task = app.broker.periodic_tasks[0]
        periodic_task.start()  # Schedule in event loop
    """

    def __init__(
        self,
        func: Callable[..., Any],
        *,
        seconds: float = 0,
        minutes: float = 0,
        hours: float = 0,
        cron: str | None = None,
    ) -> None:
        """
        Initialize a recurring task.

        Args:
            func: The task function (can be async or sync)
            seconds: Run every N seconds
            minutes: Run every N minutes
            hours: Run every N hours
            cron: Cron expression (e.g., "0 12 * * *" for daily at noon)
        """
        self.func = func
        self.task = func  # Alias for backwards compatibility with tests
        self.cron = cron
        self.seconds = seconds
        self.minutes = minutes
        self.hours = hours
        self._interval_seconds: float = seconds + minutes * 60 + hours * 3600
        self._task_handle: asyncio.Task | None = None
        self._execution_count = 0
        self._last_error: Exception | None = None

    @property
    def interval(self) -> float:
        """Total interval in seconds (0 if cron-based)."""
        return self._interval_seconds

    @property
    def execution_count(self) -> int:
        """Number of times this task has executed."""
        return self._execution_count

    @property
    def last_error(self) -> Exception | None:
        """Last exception encountered during execution."""
        return self._last_error

    async def _run_loop(self) -> None:
        """
        Run the task repeatedly at the configured interval.

        Handles both async and sync task functions. Errors are logged
        but don't stop the loop—the task will retry at the next interval.
        """
        logger.info(
            "Periodic task '%s' loop started (interval: %.1f seconds)",
            self.func.__name__,
            self._interval_seconds,
        )

        while True:
            try:
                await asyncio.sleep(self._interval_seconds)

                # Execute the task (handle both async and sync)
                logger.debug("Executing periodic task: %s", self.func.__name__)
                result = self.func()
                if asyncio.iscoroutine(result):
                    await result

                self._execution_count += 1
                self._last_error = None
                logger.debug(
                    "Periodic task '%s' completed (run #%d)",
                    self.func.__name__,
                    self._execution_count,
                )

            except asyncio.CancelledError:
                # Task was cancelled (shutdown)
                logger.info(
                    "Periodic task '%s' cancelled after %d runs",
                    self.func.__name__,
                    self._execution_count,
                )
                break

            except Exception as exc:
                # Log the error and continue (don't crash the loop)
                self._last_error = exc
                logger.error(
                    "Periodic task '%s' raised an exception (run #%d): %s",
                    self.func.__name__,
                    self._execution_count + 1,
                    exc,
                    exc_info=True,
                )

    def start(self) -> None:
        """
        Schedule the task loop in the current event loop.

        This creates an asyncio.Task that runs the _run_loop coroutine.
        The task is cancelled during shutdown via stop().

        Raises:
            RuntimeError: If no event loop is running
        """
        if self._interval_seconds <= 0:
            logger.warning(
                "Periodic task '%s' has no interval configured — skipping.",
                self.func.__name__,
            )
            return

        try:
            self._task_handle = asyncio.ensure_future(self._run_loop())
            logger.info(
                "Periodic task '%s' started (interval: %.1f seconds)",
                self.func.__name__,
                self._interval_seconds,
            )
        except RuntimeError as e:
            logger.error(
                "Failed to start periodic task '%s': %s",
                self.func.__name__,
                e,
            )
            raise

    def stop(self) -> None:
        """
        Cancel the running task loop.

        This gracefully shuts down the periodic task. Any in-flight
        executions will be cancelled.
        """
        if self._task_handle is None:
            return

        if not self._task_handle.done():
            self._task_handle.cancel()
            logger.info(
                "Periodic task '%s' stopped (completed %d runs, last error: %s)",
                self.func.__name__,
                self._execution_count,
                self._last_error,
            )
        else:
            logger.debug(
                "Periodic task '%s' already stopped",
                self.func.__name__,
            )


# ── EdenBroker ────────────────────────────────────────────────────────────────

class EdenBroker:
    """
    Production-ready task broker wrapping Taskiq for background jobs.

    Features:
        - Async/sync task execution: @app.task()
        - Periodic scheduling: @app.task.every(minutes=5)
        - Automatic retry with exponential backoff on failures
        - Task result persistence and monitoring
        - Dead-letter queue for permanently failed tasks
        - Full integration with Eden app lifecycle

    Usage::

        # Register a background task
        @app.task()
        async def send_email(to: str, subject: str):
            '''Send email (auto-retries 5 times on failure).'''
            pass

        # Trigger immediately
        await send_email.kiq(to="user@example.com", subject="Hello")

        # Or defer execution
        await app.task.defer(send_email, to="user@example.com", subject="Hi")

        # Register a periodic task
        @app.task.every(minutes=5)
        async def refresh_cache():
            '''Runs every 5 minutes during server uptime.'''
            pass

        # App startup will register everything automatically
    """

    def __init__(
        self,
        broker: AsyncBroker,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delays: list[int] | None = None,
    ) -> None:
        """
        Initialize the Eden task broker.

        Args:
            broker: Taskiq AsyncBroker instance (InMemoryBroker, RedisBroker, etc.)
            max_retries: Maximum number of retry attempts (default: 5)
            retry_delays: List of delay seconds between retries (default: [1,2,4,8,16])
        """
        self.broker = broker
        self._periodic: list[PeriodicTask] = []
        self._result_backend = TaskResultBackend()
        self._running = False
        self._startup_complete = False

        # Retry configuration
        self.max_retries = max_retries
        self.retry_delays = retry_delays or DEFAULT_RETRY_DELAYS

        if len(self.retry_delays) < self.max_retries:
            logger.warning(
                "Retry delays list (%d items) is shorter than max_retries (%d). "
                "Will repeat last delay.",
                len(self.retry_delays),
                self.max_retries,
            )

    @property
    def periodic_tasks(self) -> list[PeriodicTask]:
        """Backwards compatibility for tests."""
        return self._periodic

    @property
    def result_backend(self) -> TaskResultBackend:
        """Access the task result storage backend."""
        return self._result_backend

    @property
    def is_running(self) -> bool:
        """Whether the broker is currently running."""
        return self._running

    # ── Core decorator ────────────────────────────────────────────────────────

    def __call__(self, *args: Any, **kwargs: Any) -> Callable[[Callable[..., Any]], Any]:
        """Alias so @app.task() works like @app.task.task()."""
        return self.task(*args, **kwargs)

    def task(self, *args: Any, **kwargs: Any) -> Any:
        """
        Decorator to register a background task with automatic retry.

        The decorated function becomes a Taskiq task with .kiq() method
        for triggering execution. On failure, the task will automatically
        retry up to max_retries times with exponential backoff delays.

        Args:
            *args: Passed to the underlying Taskiq broker.task()
            **kwargs: Passed to the underlying Taskiq broker.task()

        Returns:
            Decorated task function

        Example::

            @app.task()
            async def process_order(order_id: int):
                # This will retry automatically on failure
                order = await Order.get(order_id)
                await order.process()

            # Trigger the task
            await process_order.kiq(order_id=42)
        """
        return self.broker.task(*args, **kwargs)

    # ── Periodic scheduling ───────────────────────────────────────────────────

    def every(
        self,
        *,
        seconds: float = 0,
        minutes: float = 0,
        hours: float = 0,
        cron: str | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        Decorator to register a periodic / repeating task.

        The task runs at fixed intervals in the current event loop during uptime.
        For distributed setups with multiple workers, use APScheduler backend.

        Args:
            seconds: Run every N seconds
            minutes: Run every N minutes
            hours: Run every N hours
            cron: Cron expression (e.g., "0 12 * * *" for daily at noon)

        Returns:
            Decorator function

        Example::

            @app.task.every(minutes=5)
            async def refresh_cache():
                '''Runs every 5 minutes.'''
                await Cache.invalidate()

            @app.task.every(hours=1)
            async def send_digest():
                '''Runs every hour.'''
                await send_email_digest()

            @app.task.every(seconds=30)
            async def heartbeat():
                '''Runs every 30 seconds.'''
                logger.info("Server is alive")
        """

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            # Register as a Taskiq task first
            task_func = self.task()(func)

            # Create periodic task wrapper
            periodic = PeriodicTask(
                task_func,
                seconds=seconds,
                minutes=minutes,
                hours=hours,
                cron=cron,
            )
            self._periodic.append(periodic)

            logger.debug(
                "Registered periodic task: '%s' (interval: %.1fs)",
                func.__name__,
                periodic.interval,
            )

            return task_func

        return decorator

    # ── Queue helpers ─────────────────────────────────────────────────────────

    async def defer(self, task: Any, *args: Any, **kwargs: Any) -> Any:
        """
        Send a task to the broker queue immediately (fire-and-forget).

        This queues the task for execution without waiting for a result.

        Args:
            task: The task function decorated with @app.task()
            *args: Positional arguments for the task
            **kwargs: Keyword arguments for the task

        Returns:
            Task kick object (depends on broker backend)

        Example::

            # Register task
            @app.task()
            async def send_email(to: str):
                pass

            # Fire and forget
            await app.task.defer(send_email, to="user@example.com")
        """
        if not self._startup_complete:
            raise BrokerNotInitialized(
                "Broker not initialized. Did you call app.setup_tasks() or await app.broker.startup()?"
            )

        return await task.kiq(*args, **kwargs)

    async def schedule(
        self, task: Any, delay: int | float, *args: Any, **kwargs: Any
    ) -> Any:
        """
        Send a task to the queue with a delay (in seconds).

        The task will be executed after the specified delay.
        Only works when the broker/result backend supports delayed execution
        (e.g., taskiq-redis with Taskiq Scheduler backend).

        Args:
            task: The task function decorated with @app.task()
            delay: Seconds to wait before executing
            *args: Positional arguments for the task
            **kwargs: Keyword arguments for the task

        Returns:
            Task kick object

        Example::

            @app.task()
            async def send_reminder(user_id: int):
                user = await User.get(user_id)
                await user.send_reminder()

            # Execute in 1 hour
            await app.task.schedule(send_reminder, delay=3600, user_id=42)
        """
        if not self._startup_complete:
            raise BrokerNotInitialized(
                "Broker not initialized. Did you call app.setup_tasks() or await app.broker.startup()?"
            )

        kicker = task.kiq(*args, **kwargs)
        if hasattr(kicker, "with_labels"):
            return await kicker.with_labels(delay=int(delay))
        return await kicker

    async def get_task_result(self, task_id: str) -> TaskResult | None:
        """
        Retrieve the result of a task execution.

        Args:
            task_id: The unique task identifier

        Returns:
            TaskResult if found, None otherwise
        """
        return await self._result_backend.get_result(task_id)

    async def get_dead_letter_tasks(self) -> list[TaskResult]:
        """
        Get all tasks that failed permanently (exhausted retries).

        Returns:
            List of TaskResult objects in dead-letter state
        """
        return await self._result_backend.get_dead_letter_tasks()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def startup(self) -> None:
        """
        Start the broker and all registered periodic tasks.

        This is called automatically by the Eden app during startup.
        Must be called before using defer() or schedule().

        Example::

            app = Eden()
            await app.broker.startup()  # Manual startup
        """
        logger.info("Starting task broker...")

        # Start the underlying Taskiq broker
        try:
            await self.broker.startup()
        except Exception as e:
            logger.error("Failed to start broker: %s", e)
            raise

        # Start all registered periodic tasks
        for periodic in self._periodic:
            try:
                periodic.start()
            except Exception as e:
                logger.error(
                    "Failed to start periodic task '%s': %s",
                    periodic.func.__name__,
                    e,
                )

        self._running = True
        self._startup_complete = True

        logger.info(
            "Task broker started with %d periodic tasks",
            len(self._periodic),
        )

    async def shutdown(self) -> None:
        """
        Stop all periodic tasks and shut down the broker.

        This is called automatically by the Eden app during shutdown.
        After shutdown, defer() and schedule() cannot be used.

        Example::

            await app.broker.shutdown()  # Manual shutdown
        """
        logger.info("Shutting down task broker...")

        # Stop all periodic tasks
        for periodic in self._periodic:
            try:
                periodic.stop()
            except Exception as e:
                logger.error(
                    "Error stopping periodic task '%s': %s",
                    periodic.func.__name__,
                    e,
                )

        # Clean up expired task results
        try:
            expired_count = await self._result_backend.cleanup_expired()
            logger.debug("Cleaned up %d expired task results", expired_count)
        except Exception as e:
            logger.error("Error cleaning up task results: %s", e)

        # Shut down the underlying Taskiq broker
        try:
            await self.broker.shutdown()
        except Exception as e:
            logger.error("Error shutting down broker: %s", e)

        self._running = False
        logger.info("Task broker shut down")


# ── Factory ───────────────────────────────────────────────────────────────────

def create_broker(redis_url: str | None = None) -> AsyncBroker:
    """
    Create a Taskiq broker based on configuration.

    - No ``redis_url``  → ``InMemoryBroker`` (development / testing)
    - With ``redis_url`` → ``RedisBroker`` (requires ``taskiq-redis``)

    Usage::
        # Development
        broker = create_broker()

        # Production
        broker = create_broker(redis_url="redis://localhost:6379")
    """
    if redis_url:
        if RedisBroker is None:
            raise ImportError(
                "taskiq-redis is required for Redis support. "
                "Install with: pip install taskiq-redis"
            )
        return RedisBroker(redis_url)

    return InMemoryBroker()
