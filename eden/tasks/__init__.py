"""
Eden — Task Queue Integration

Provides EdenBroker: a comprehensive wrapper around Taskiq for background tasks,
periodic scheduling, and comprehensive error recovery with integration to app lifecycle.

Key Features:
    - One-shot background tasks: @app.task() with automatic DI
    - Periodic/repeating tasks: @app.task.every(minutes=5) or @app.task.every(cron="0 0 * * *")
    - Error recovery with exponential backoff and custom retry logic
    - Integrated with Eden app lifecycle (startup/shutdown)
"""

from __future__ import annotations

import asyncio
import functools
import json
import logging
import traceback
from collections.abc import Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Any, TypeVar, Optional, List, Union

try:
    from taskiq import AsyncBroker, InMemoryBroker
except ImportError:

    class AsyncBroker:
        pass

    class InMemoryBroker:
        pass

    _HAS_TASKIQ = False
else:
    _HAS_TASKIQ = True

try:
    from taskiq_redis import PubSubBroker as RedisBroker
except ImportError:
    try:
        from taskiq_redis import RedisStreamBroker as RedisBroker
    except ImportError:
        RedisBroker = None

try:
    from croniter import croniter
except ImportError:
    croniter = None

from eden.tasks.exceptions import (
    TaskExecutionError,
    MaxRetriesExceeded,
    BrokerNotInitialized,
)

logger = logging.getLogger("eden.tasks")

T = TypeVar("T")

# Retry configuration: exponential backoff (1s, 2s, 4s, 8s, 16s)
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAYS = [1, 2, 4, 8, 16]  # seconds


# ── Task Result Storage ───────────────────────────────────────────────────────


@dataclass
class TaskResult:
    """Represents the result of a task execution."""

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
        for key in ["created_at", "started_at", "completed_at"]:
            if data[key] is not None:
                if isinstance(data[key], datetime):
                    data[key] = data[key].isoformat()
        if data["result"] is not None:
            try:
                json.dumps(data["result"])
            except (TypeError, ValueError):
                data["result"] = str(data["result"])
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskResult:
        """Reconstruct result from dictionary."""
        for key in ["created_at", "started_at", "completed_at"]:
            if data.get(key) and isinstance(data[key], str):
                data[key] = datetime.fromisoformat(data[key])
        return cls(**data)


class TaskResultBackend:
    """In-memory storage for task execution results and dead-letter queue."""

    def __init__(self) -> None:
        self._results: dict[str, TaskResult] = {}
        self._dead_letter: list[TaskResult] = []

    async def store_result(self, task_id: str, result: TaskResult) -> None:
        """Store a task result."""
        self._results[task_id] = result
        logger.debug("Stored task result: %s (status=%s)", task_id, result.status)
        if result.status == "dead_letter":
            self._dead_letter.append(result)

    async def get_result(self, task_id: str) -> TaskResult | None:
        """Retrieve a stored task result."""
        return self._results.get(task_id)

    async def cleanup_expired(self) -> int:
        """Remove expired results based on TTL."""
        now = datetime.now()
        expired_ids = []
        for task_id, result in self._results.items():
            if result.completed_at:
                if (now - result.completed_at).total_seconds() > result.ttl_seconds:
                    expired_ids.append(task_id)

        for task_id in expired_ids:
            del self._results[task_id]
        logger.debug("Cleaned up %d expired task results", len(expired_ids))
        return len(expired_ids)

    async def get_dead_letter_tasks(self) -> list[TaskResult]:
        """Get all tasks in the dead-letter queue."""
        return list(self._dead_letter)

    async def clear_dead_letter(self) -> int:
        """Clear dead letters."""
        count = len(self._dead_letter)
        self._dead_letter.clear()
        return count


# ── Periodic Task Descriptor ──────────────────────────────────────────────────


class PeriodicTask:
    """Holds the schedule config for a periodic task registered via .every()."""

    def __init__(
        self,
        func: Callable[..., Any],
        broker: EdenBroker,
        *,
        seconds: float = 0,
        minutes: float = 0,
        hours: float = 0,
        cron: str | None = None,
    ) -> None:
        self.func = func
        self.task = func  # Alias for consistency with tests
        self.broker = broker
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

    async def _run_loop(self) -> None:
        """Run the task repeatedly based on interval or cron."""
        logger.info(
            "Periodic task '%s' loop started (schedule: %s)",
            self.func.__name__,
            self.cron if self.cron else f"{self._interval_seconds}s interval",
        )

        while True:
            try:
                # Calculate wait time
                if self.cron and croniter:
                    now = datetime.now()
                    it = croniter(self.cron, now)
                    next_run = it.get_next(datetime)
                    wait_seconds = (next_run - now).total_seconds()
                    if wait_seconds > 0:
                        await asyncio.sleep(wait_seconds)
                elif self._interval_seconds > 0:
                    await asyncio.sleep(self._interval_seconds)
                else:
                    logger.error("Periodic task '%s' has no valid schedule.", self.func.__name__)
                    break

                # Distributed locking for periodic tasks
                lock = None
                lock_acquired = False
                if self.broker._redis_lock_client:
                    lock_key = f"eden:periodic_task_lock:{self.func.__name__}"
                    try:
                        lock = self.broker._redis_lock_client.lock(lock_key, timeout=300.0)
                        # Try to acquire lock with timeout
                        try:
                            await asyncio.wait_for(lock.acquire(), timeout=10.0)
                            lock_acquired = True
                        except asyncio.TimeoutError:
                            lock_acquired = False
                            logger.warning(
                                "Timeout acquiring lock for periodic task '%s'", self.func.__name__
                            )
                    except Exception as e:
                        logger.error(
                            "Error with lock for periodic task '%s': %s",
                            self.func.__name__,
                            e,
                        )

                if self.broker._redis_lock_client and not lock_acquired:
                    logger.warning(
                        "Could not acquire lock for periodic task '%s', skipping this run",
                        self.func.__name__,
                    )
                    continue

                try:
                    logger.debug("Executing periodic task: %s", self.func.__name__)

                    # Execute via kiq to use the broker's execution logic (including DI)
                    if hasattr(self.func, "kiq"):
                        await self.func.kiq()
                    else:
                        # Fallback for non-taskiq decorated functions
                        result = self.func()
                        if asyncio.iscoroutine(result):
                            await result

                    self._execution_count += 1
                    self._last_error = None
                except Exception as exc:
                    self._last_error = exc
                    logger.error(
                        "Periodic task '%s' failed (run #%d): %s",
                        self.func.__name__,
                        self._execution_count + 1,
                        exc,
                        exc_info=True,
                    )
                finally:
                    # Release the lock if we acquired it
                    if lock and lock_acquired:
                        try:
                            # For redis.asyncio Lock, locked() is a method that returns bool
                            if hasattr(lock, "locked") and callable(lock.locked):
                                if lock.locked():
                                    await lock.release()
                        except Exception as e:
                            logger.error(
                                "Error releasing lock for periodic task '%s': %s",
                                self.func.__name__,
                                e,
                            )

            except asyncio.CancelledError:
                break
            except Exception as exc:
                # This catches any exception in the wait or lock acquisition that we didn't handle above?
                logger.error(
                    "Unexpected error in periodic task '%s' loop: %s",
                    self.func.__name__,
                    exc,
                    exc_info=True,
                )
                # We don't break the loop on unexpected errors? We continue to the next iteration.

    def start(self) -> None:
        """Schedule the task loop in the current event loop."""
        if self._interval_seconds <= 0 and not self.cron:
            return

        if self.cron and not croniter:
            logger.error(
                "croniter not installed. Cron task '%s' will not start.", self.func.__name__
            )
            return

        self._task_handle = asyncio.create_task(self._run_loop())

    def stop(self) -> None:
        """Cancel the running task loop."""
        if self._task_handle and not self._task_handle.done():
            self._task_handle.cancel()


# ── EdenBroker ────────────────────────────────────────────────────────────────


class EdenBroker:
    """Production-ready task broker wrapping Taskiq for background jobs."""

    def __init__(
        self,
        broker: AsyncBroker,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delays: list[int] | None = None,
    ) -> None:
        """Initialize the Eden task broker."""
        self.broker = broker
        self.app: Any = None  # Set by Eden app
        self._periodic: list[PeriodicTask] = []
        self._result_backend = TaskResultBackend()
        self._running = False
        self._startup_complete = False

        self.max_retries = max_retries
        self.retry_delays = retry_delays or DEFAULT_RETRY_DELAYS

        # Extract redis_url from broker if available (set by create_broker)
        self._redis_lock_client = None
        redis_url = getattr(broker, "_redis_url", None)
        if redis_url:
            try:
                import redis.asyncio as redis

                self._redis_lock_client = redis.from_url(redis_url)
            except ImportError:
                logger.warning(
                    "redis package not installed, distributed lock for periodic tasks will not be available"
                )

    @property
    def periodic_tasks(self) -> list[PeriodicTask]:
        """Backwards compatibility for tests."""
        return self._periodic

    @property
    def is_running(self) -> bool:
        """Whether the broker is currently running."""
        return self._running

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Alias so @app.task() works like @app.task.task()."""
        return self.task(*args, **kwargs)

    def task(
        self,
        *args: Any,
        max_retries: int | None = None,
        retry_delays: list[int] | None = None,
        **kwargs: Any,
    ) -> Any:
        # Support both @app.task and @app.task()
        if len(args) == 1 and callable(args[0]):
            return self.task()(args[0])

        retries = max_retries if max_retries is not None else self.max_retries
        delays = retry_delays if retry_delays is not None else self.retry_delays

        def decorator(func: Callable[..., Any]) -> Any:
            # Wrap the function to inject Eden dependencies and handle retries
            handler = self._wrap_task_function(func, retries, delays)
            # Register with the underlying taskiq broker
            # Taskiq's task() decorator also supports both styles, but we
            # pass kwargs here to be safe.
            return self.broker.task(*args, **kwargs)(handler)

        return decorator

    def every(
        self,
        *,
        seconds: float = 0,
        minutes: float = 0,
        hours: float = 0,
        cron: str | None = None,
    ) -> Callable[[Callable[..., Any]], Any]:
        """Decorator to register a periodic task."""

        def decorator(func: Callable[..., Any]) -> Any:
            # Ensure it's registered as a task first
            # We call self.task() to get the wrapped handler registered
            task_func = self.task()(func)

            periodic = PeriodicTask(
                task_func,
                self,
                seconds=seconds,
                minutes=minutes,
                hours=hours,
                cron=cron,
            )
            self._periodic.append(periodic)
            return task_func

        return decorator

    def _wrap_task_function(
        self, func: Callable[..., Any], max_retries: int, retry_delays: list[int]
    ) -> Callable[..., Any]:
        """Wrap a task function to add DI and retry support."""

        @functools.wraps(func)
        async def task_handler(*args: Any, **kwargs: Any) -> Any:
            from eden.dependencies import DependencyResolver

            # Use DependencyResolver with current app instance
            async with DependencyResolver() as resolver:
                # Merge explicitly passed kwargs with injected ones
                try:
                    dep_kwargs = await resolver.resolve(func, app=self.app)
                except Exception as e:
                    logger.error(
                        "Failed to resolve dependencies for task '%s': %s", func.__name__, e
                    )
                    raise TaskExecutionError(f"DI failure in task {func.__name__}") from e

                final_kwargs = {**dep_kwargs, **kwargs}

                # Execution loop with retries
                attempt = 0
                while attempt <= max_retries:
                    try:
                        if asyncio.iscoroutinefunction(func):
                            return await func(*args, **final_kwargs)
                        else:
                            return func(*args, **final_kwargs)
                    except Exception as e:
                        attempt += 1
                        if attempt > max_retries:
                            logger.error(
                                "Task '%s' failed after %d retries.", func.__name__, max_retries
                            )

                            # Record result as failure (simplified for now)
                            error_info = TaskResult(
                                task_id=str(getattr(task_handler, "task_id", "unknown")),
                                task_name=func.__name__,
                                status="dead_letter",
                                error=str(e),
                                error_traceback=traceback.format_exc(),
                                retries=attempt - 1,
                                completed_at=datetime.now(),
                            )
                            await self._result_backend.store_result(error_info.task_id, error_info)
                            raise MaxRetriesExceeded(
                                f"Task {func.__name__} failed after {max_retries} retries"
                            ) from e

                        delay = retry_delays[min(attempt - 1, len(retry_delays) - 1)]
                        logger.warning(
                            "Task '%s' failed (attempt %d). Retrying in %ds...",
                            func.__name__,
                            attempt,
                            delay,
                        )
                        await asyncio.sleep(delay)

        return task_handler

    async def defer(self, task: Any, *args: Any, **kwargs: Any) -> Any:
        """Send a task to the broker queue immediately."""
        if not self._startup_complete:
            raise BrokerNotInitialized("Broker not started.")
        return await task.kiq(*args, **kwargs)

    async def schedule(self, task: Any, delay: int | float, *args: Any, **kwargs: Any) -> Any:
        """Send a task to the queue with a delay."""
        if not self._startup_complete:
            raise BrokerNotInitialized("Broker not started.")
        kicker = task.kiq(*args, **kwargs)
        if hasattr(kicker, "with_labels"):
            return await kicker.with_labels(delay=int(delay))
        return await kicker

    async def startup(self) -> None:
        """Start the broker and all registered periodic tasks."""
        if self._running:
            return

        logger.info("Starting Eden Task Broker...")
        await self.broker.startup()

        for periodic in self._periodic:
            periodic.start()

        self._running = True
        self._startup_complete = True

    async def shutdown(self) -> None:
        """Stop all periodic tasks and shut down the broker."""
        if not self._running:
            return

        logger.info("Shutting down Eden Task Broker...")
        for periodic in self._periodic:
            periodic.stop()

        await self.broker.shutdown()
        self._running = False
        self._startup_complete = False


# ── Factory ───────────────────────────────────────────────────────────────────


def create_broker(redis_url: str | None = None) -> AsyncBroker:
    """Create a Taskiq broker based on configuration."""
    if redis_url:
        if RedisBroker is None:
            raise ImportError("taskiq-redis required for Redis support.")
        broker = RedisBroker(redis_url)
        # Attach redis_url for distributed lock detection
        broker._redis_url = redis_url  # type: ignore[attr-defined]
        return broker
    return InMemoryBroker()


__all__ = [
    "EdenBroker",
    "PeriodicTask",
    "TaskResult",
    "TaskResultBackend",
    "create_broker",
]
