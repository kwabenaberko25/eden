from __future__ import annotations
import inspect
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


import asyncio
import functools
import json
import logging
import traceback
import uuid
from collections.abc import Callable
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta, timezone
from typing import Any, TypeVar, Optional, List, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from eden.core.backends.base import DistributedBackend

try:
    from taskiq import AsyncBroker, InMemoryBroker
except ImportError:

    class AsyncBroker:
        """Minimal AsyncBroker fallback used when taskiq is not installed.
        Provides a very small in-process task wrapper compatible with
        EdenBroker's usage (task decorator, kicker().with_labels().kiq, etc.).
        """

        def task(self, *args, **kwargs):
            def decorator(func):
                # Lightweight task wrapper exposing .kiq() and .kicker().with_labels().kiq()
                class _Task:
                    def __init__(self, func):
                        self._handler = func

                        async def _kiq(*a, **kw):
                            # Support calling handler with a 'context' kwarg
                            if inspect.iscoroutinefunction(self._handler):
                                return await self._handler(*a, **kw)
                            res = self._handler(*a, **kw)
                            if asyncio.iscoroutine(res):
                                return await res
                            return res

                        self.kiq = _kiq

                    def kicker(self):
                        parent = self

                        class Kicker:
                            def __init__(self, parent):
                                self._parent = parent
                                self._labels: dict[str, Any] = {}

                            def with_labels(self, **labels):
                                self._labels.update(labels)
                                return self

                            async def kiq(self, *a, **kw):
                                # Create a simple context object compatible with Eden's expectations
                                ctx = type("_TaskIQContext", (), {})()
                                ctx.task_id = str(uuid.uuid4())
                                ctx.labels = self._labels
                                kw = {**kw, "context": ctx}
                                return await parent.kiq(*a, **kw)

                        return Kicker(parent)

                    # Allow the task object to be callable directly (not generally used)
                    def __call__(self, *a, **kw):
                        return self._handler(*a, **kw)

                return _Task(func)

            return decorator

    class InMemoryBroker(AsyncBroker):
        """In-process broker stub providing startup/shutdown no-ops for Eden's lifecycle.
        This is intentionally minimal — for development/test environments only.
        """

        async def startup(self) -> None:
            return None

        async def shutdown(self) -> None:
            return None

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
    status: str  # 'pending', 'running', 'success', 'failed', 'dead_letter'
    result: Any = None
    error: str | None = None
    error_traceback: str | None = None
    retries: int = 0
    correlation_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    progress: float = 0.0
    status_message: str | None = None
    metadata: dict[str, Any] | None = None
    ttl_seconds: int = 604800  # 7 days default
    _version: int = 1  # Schema version for forward-compatible deserialization

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
        """Reconstruct result from dictionary.
        
        Tolerant of extra/missing keys for forward-compatible deserialization
        across framework upgrades.
        """
        for key in ["created_at", "started_at", "completed_at"]:
            if data.get(key) and isinstance(data[key], str):
                try:
                    data[key] = datetime.fromisoformat(data[key])
                except (ValueError, TypeError):
                    data[key] = None
        # Filter to only fields the dataclass actually accepts
        import dataclasses
        valid_fields = {f.name for f in dataclasses.fields(cls)}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)


class TaskResultBackend:
    """Backend for storing and retrieving task results."""

    def __init__(self, backend: Optional[DistributedBackend] = None) -> None:
        self._distributed = backend
        self._local_results: dict[str, TaskResult] = {}
        self._dead_letter: list[TaskResult] = []
        self._prefix = "eden:tasks:result:"

    async def store_result(self, task_id: str, result: TaskResult) -> None:
        """Store a task result."""
        if self._distributed:
            # TTL for result (default 7 days)
            await self._distributed.set(self._prefix + task_id, result.to_dict(), ttl=result.ttl_seconds)
            # If failed, add to a set of dead-letter tasks for easy retrieval
            if result.status == "dead_letter":
                dl_key = "eden:tasks:dead_letter"
                lock_key = "eden:tasks:locks:dead_letter"
                
                import uuid
                identifier = str(uuid.uuid4())
                
                # Acquire lock for DLQ read-modify-write
                lock_acquired = await self._distributed.acquire_lock(lock_key, timeout=5.0, identifier=identifier)
                try:
                    current_dl = await self._distributed.get(dl_key) or []
                    if task_id not in current_dl:
                        current_dl.append(task_id)
                        # Prune DLQ: keep only last 1000 entries to prevent unbounded growth
                        if len(current_dl) > 1000:
                            current_dl = current_dl[-1000:]
                        # Store with TTL matching result TTL (default 7 days)
                        await self._distributed.set(dl_key, current_dl, ttl=result.ttl_seconds)
                finally:
                    if lock_acquired:
                        await self._distributed.release_lock(lock_key, identifier)
        
        self._local_results[task_id] = result
        logger.debug("Stored task result: %s (status=%s)", task_id, result.status)
        if result.status == "dead_letter" and result not in self._dead_letter:
            self._dead_letter.append(result)

    async def get_result(self, task_id: str) -> TaskResult | None:
        """Retrieve a stored task result."""
        if self._distributed:
            data = await self._distributed.get(self._prefix + task_id)
            if data:
                return TaskResult.from_dict(data)
        return self._local_results.get(task_id)

    async def get_all_results(self, limit: int = 100) -> list[TaskResult]:
        """Get the most recent task results (local only for now)."""
        return sorted(
            self._local_results.values(), 
            key=lambda x: x.created_at, 
            reverse=True
        )[:limit]

    async def cleanup_expired(self) -> int:
        """Remove expired results (local only). Redis handles TTL automatically."""
        now = datetime.now(timezone.utc)
        expired_ids = []
        for task_id, result in self._local_results.items():
            completed_at = result.completed_at
            if completed_at is not None:
                if (now - completed_at).total_seconds() > result.ttl_seconds:
                    expired_ids.append(task_id)

        for task_id in expired_ids:
            # Check if it was in dead_letter
            result = self._local_results.get(task_id)
            if result and result in self._dead_letter:
                self._dead_letter.remove(result)
            del self._local_results[task_id]
            
        return len(expired_ids)

    async def get_dead_letter_tasks(self) -> list[TaskResult]:
        """Get all tasks in the dead-letter queue."""
        if self._distributed:
            dl_key = "eden:tasks:dead_letter"
            ids = await self._distributed.get(dl_key) or []
            results = []
            for tid in ids:
                res = await self.get_result(tid)
                if res:
                    results.append(res)
            return results
        return list(self._dead_letter)

    async def clear_dead_letter(self) -> int:
        """Clear dead letters."""
        if self._distributed:
            await self._distributed.delete("eden:tasks:dead_letter")
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

        next_run = datetime.now(timezone.utc)
        while True:
            try:
                now = datetime.now(timezone.utc)
                # Calculate next wait time
                if self.cron and croniter:
                    it = croniter(self.cron, now)
                    next_run = it.get_next(datetime)
                    wait_seconds = (next_run - now).total_seconds()
                    # Add a tiny buffer to avoid precision issues
                    if wait_seconds > 0:
                        await asyncio.sleep(wait_seconds + 0.1)
                elif self._interval_seconds > 0:
                    next_run += timedelta(seconds=self._interval_seconds)
                    # Coalesce: if next_run fell behind, snap to now + interval
                    # This prevents burst catch-up execution when tasks are slow
                    if next_run < now:
                        logger.debug(
                            "Periodic task '%s' missed schedule (coalesced). "
                            "Snapping to now + interval.",
                            self.func.__name__,
                        )
                        next_run = now + timedelta(seconds=self._interval_seconds)
                    wait_seconds = (next_run - datetime.now(timezone.utc)).total_seconds()
                    if wait_seconds > 0:
                        await asyncio.sleep(wait_seconds)
                    else:
                        next_run = datetime.now(timezone.utc)
                else:
                    logger.error("Periodic task '%s' has no valid schedule.", self.func.__name__)
                    break

                # distributed coordination
                lock_acquired = False
                lock_key = f"eden:periodic_task:{self.func.__name__}"
                identifier = str(uuid.uuid4())
                
                backend = getattr(self.broker, "_distributed_backend", None)
                if backend:
                    try:
                        # 1. Check last run time to prevent double-execution in same interval
                        last_run_key = f"eden:task_last_run:{self.func.__name__}"
                        last_run = await backend.get(last_run_key)
                        now_ts = datetime.now(timezone.utc).timestamp()
                        
                        if last_run:
                            try:
                                if (now_ts - float(last_run)) < (self._interval_seconds * 0.8):
                                    logger.debug("periodic task %s skipped (recently run)", self.func.__name__)
                                    continue
                            except (ValueError, TypeError):
                                pass

                        # 2. Acquire lock to prevent race condition
                        lock_ttl = max(30, int(self._interval_seconds * 0.8)) if self._interval_seconds > 0 else 30
                        lock_acquired = await backend.acquire_lock(
                            lock_key, timeout=float(lock_ttl), identifier=identifier
                        )
                        
                        if not lock_acquired:
                            logger.debug("periodic task %s lock failed", self.func.__name__)
                            continue

                        # 3. Update last run time immediately
                        await backend.set(last_run_key, str(now_ts), ttl=int(max(3600.0, float(self._interval_seconds * 2))))
                        logger.debug("periodic task %s coordination success", self.func.__name__)
                        
                    except Exception as e:
                        logger.error("Coordination error for periodic task '%s': %s", self.func.__name__, e)
                        if backend and not lock_acquired:
                            continue

                try:
                    logger.debug("Executing periodic task: %s", self.func.__name__)
                    start_time = datetime.now(timezone.utc)
                    
                    # Periodic tasks act as the initiator correlation ID
                    correlation_id = f"periodic-{self.func.__name__}-{int(start_time.timestamp())}"
                    real_task_id = None
                    
                    # Execute via kiq to use the broker's execution logic (including DI)
                    if hasattr(self.func, "kiq"):
                        from eden.context import set_request_id, reset_request_id
                        token = set_request_id(correlation_id)
                        try:
                            # Capture Taskiq's native ID if available
                            kicked = await self.func.kiq()
                            if hasattr(kicked, "task_id"):
                                real_task_id = kicked.task_id
                        finally:
                            reset_request_id(token)
                            
                        status_val = "dispatched"
                        status_msg = f"Task successfully dispatched to broker queue. (Broker ID: {real_task_id or 'unknown'})"
                    else:
                        result = self.func()
                        if asyncio.iscoroutine(result):
                            await result
                        status_val = "success"
                        status_msg = None

                    self._execution_count += 1
                    self._last_error = None
                    
                    # Record success
                    success_info = TaskResult(
                        task_id=correlation_id,
                        task_name=self.func.__name__,
                        status=status_val,
                        started_at=start_time,
                        completed_at=datetime.now(timezone.utc),
                        status_message=status_msg,
                        metadata={"broker_task_id": real_task_id} if real_task_id else None
                    )
                    await self.broker._result_backend.store_result(correlation_id, success_info)

                except Exception as exc:
                    self._last_error = exc
                    logger.error(
                        "Periodic task '%s' failed (run #%d): %s",
                        self.func.__name__,
                        self._execution_count + 1,
                        exc,
                        exc_info=True,
                    )
                    
                    # Record failure
                    error_info = TaskResult(
                        task_id=correlation_id if 'correlation_id' in locals() else f"periodic-{self.func.__name__}-{int(datetime.now(timezone.utc).timestamp())}",
                        task_name=self.func.__name__,
                        status="failed",
                        error=str(exc),
                        error_traceback=traceback.format_exc(),
                        completed_at=datetime.now(timezone.utc),
                    )
                    await self.broker._result_backend.store_result(error_info.task_id, error_info)

                finally:
                    if lock_acquired and backend:
                        await backend.release_lock(lock_key, identifier)

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(
                    "Unexpected error in periodic task '%s' loop: %s",
                    self.func.__name__,
                    exc,
                )
                await asyncio.sleep(1) # prevent tight loop on error

    def start(self) -> None:
        """Schedule the task loop in the current event loop."""
        if self._interval_seconds <= 0 and not self.cron:
            return

        if self.cron and not croniter:
            logger.error(
                "croniter not installed. Cron task '%s' will not start.", self.func.__name__
            )
            return

        from eden.tenancy.context import spawn_safe_task
        self._task_handle = spawn_safe_task(
            self._run_loop(), name=f"periodic-{self.func.__name__}"
        )

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
        default_timeout: int = 0,
    ) -> None:
        """Initialize the Eden task broker.
        
        Args:
            broker: The underlying Taskiq broker (InMemoryBroker or RedisBroker)
            max_retries: Default max retries for tasks
            retry_delays: Default retry delay schedule (seconds per attempt)
            default_timeout: Default task execution timeout in seconds (0=no timeout)
        """
        self.broker = broker
        self.app: Any = None  # Set by Eden app
        self._periodic: list[PeriodicTask] = []
        self._result_backend = TaskResultBackend()
        self._running = False
        self._startup_complete = False

        self.max_retries = max_retries
        self.retry_delays = retry_delays or DEFAULT_RETRY_DELAYS
        self.default_timeout = default_timeout

        # Signal hooks — lists of async callables
        # Called with (task_name: str, task_id: str, args, kwargs)
        self._on_task_prerun: list[Callable] = []
        self._on_task_postrun: list[Callable] = []
        # Called with (task_name: str, task_id: str, result)
        self._on_task_success: list[Callable] = []
        # Called with (task_name: str, task_id: str, exception)
        self._on_task_failure: list[Callable] = []

        # Revocation tracking
        self._revocation_prefix = "eden:tasks:revoked:"
        self._local_revoked: set[str] = set()

        # Distributed coordination
        self._distributed_backend: DistributedBackend | None = None
        
        # Extract redis_url from broker if available (set by create_broker)
        # This fallback remains for direct redis usage if no backend set
        self._redis_lock_client = None
        redis_url = getattr(broker, "_redis_url", None)
        if redis_url:
            try:
                import redis.asyncio as redis

                self._redis_lock_client = redis.from_url(redis_url)
            except ImportError:
                logger.warning(
                    "redis package not installed, legacy distributed lock fallback will not be available"
                )

    @property
    def periodic_tasks(self) -> list[PeriodicTask]:
        """Backwards compatibility for tests."""
        return self._periodic

    @property
    def is_running(self) -> bool:
        """Whether the broker is currently running."""
        return self._running

    @classmethod
    def get_current(cls) -> EdenBroker | None:
        """Get the current active EdenBroker instance."""
        from eden.app import Eden
        app = Eden.get_current()
        if app:
            return app.broker
        return None

    async def get_result(self, task_id: str) -> TaskResult | None:
        """Retrieve a stored task result."""
        return await self._result_backend.get_result(task_id)

    async def get_all_results(self, limit: int = 100) -> list[TaskResult]:
        """Get the most recent task results."""
        return await self._result_backend.get_all_results(limit)

    async def get_dead_letter_tasks(self) -> list[TaskResult]:
        """Get all tasks in the dead-letter queue."""
        return await self._result_backend.get_dead_letter_tasks()

    def set_distributed_backend(self, backend: DistributedBackend) -> None:
        """Set a distributed backend for task coordination."""
        self._distributed_backend = backend
        # Re-initialize result backend with the distributed backend
        self._result_backend = TaskResultBackend(backend)

    # ── Signal Hook Registration ──────────────────────────────────────────

    def on_task_prerun(self, func: Callable) -> Callable:
        """Register a callback invoked before a task executes.
        
        The callback receives (task_name: str, task_id: str).
        
        Example::
        
            @app.task.on_task_prerun
            async def log_start(task_name, task_id):
                print(f"Starting {task_name} ({task_id})")
        """
        self._on_task_prerun.append(func)
        return func

    def on_task_postrun(self, func: Callable) -> Callable:
        """Register a callback invoked after a task completes (success or failure).
        
        The callback receives (task_name: str, task_id: str, status: str).
        """
        self._on_task_postrun.append(func)
        return func

    def on_task_success(self, func: Callable) -> Callable:
        """Register a callback invoked after a task succeeds.
        
        The callback receives (task_name: str, task_id: str, result: Any).
        """
        self._on_task_success.append(func)
        return func

    def on_task_failure(self, func: Callable) -> Callable:
        """Register a callback invoked after a task permanently fails (exhausts retries).
        
        The callback receives (task_name: str, task_id: str, exception: Exception).
        """
        self._on_task_failure.append(func)
        return func

    async def _fire_signal(self, signal_list: list[Callable], *args: Any) -> None:
        """Fire all callbacks in a signal list, swallowing individual errors."""
        for cb in signal_list:
            try:
                if inspect.iscoroutinefunction(cb):
                    await cb(*args)
                else:
                    cb(*args)
            except Exception as e:
                logger.error("Error in task signal callback %s: %s", cb.__name__, e)

    # ── Task Revocation ───────────────────────────────────────────────────

    async def revoke(self, task_id: str, ttl: int = 3600) -> None:
        """Mark a task as revoked. It will be skipped when a worker picks it up.
        
        Args:
            task_id: The ID of the task to revoke
            ttl: How long to keep the revocation flag (seconds, default 1 hour)
        """
        self._local_revoked.add(task_id)
        if self._distributed_backend:
            await self._distributed_backend.set(
                self._revocation_prefix + task_id, "1", ttl=ttl
            )
        logger.info("Task %s revoked", task_id)

    async def is_revoked(self, task_id: str) -> bool:
        """Check if a task has been revoked."""
        if task_id in self._local_revoked:
            return True
        if self._distributed_backend:
            result = await self._distributed_backend.get(self._revocation_prefix + task_id)
            return result is not None
        return False

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Alias so @app.task() works like @app.task.task()."""
        return self.task(*args, **kwargs)

    def task(
        self,
        *args: Any,
        max_retries: int | None = None,
        retry_delays: list[int] | None = None,
        exponential_backoff: bool = True,
        timeout: int | None = None,
        **kwargs: Any,
    ) -> Any:
        """Register a background task.
        
        Args:
            max_retries: Max retry attempts on failure (default: broker's max_retries)
            retry_delays: Custom retry delay schedule [1, 2, 4, ...] seconds
            exponential_backoff: Whether to use exponential backoff on retries
            timeout: Max execution time in seconds (0 or None = no timeout)
            
        Usage::
        
            @app.task()
            async def send_email(to: str, subject: str):
                ...
            
            # Dispatch immediately
            await send_email.dispatch("user@example.com", "Hello")
            
            # Dispatch with delay
            await send_email.dispatch_after(60, "user@example.com", "Hello")
        """
        # Support both @app.task and @app.task()
        if len(args) == 1 and callable(args[0]):
            return self.task()(args[0])

        # Check for aliases in kwargs (common in older tests or other frameworks)
        mr = max_retries if max_retries is not None else kwargs.pop("retries", None)
        rd = retry_delays if retry_delays is not None else kwargs.pop("delays", None)

        target_retries = mr if mr is not None else self.max_retries
        target_delays = rd if rd is not None else self.retry_delays
        target_timeout = timeout if timeout is not None else self.default_timeout

        def decorator(func: Callable[..., Any]) -> Any:
            # Wrap the function to inject Eden dependencies and handle retries
            handler = self._wrap_task_function(
                func, 
                target_retries, 
                target_delays,
                exponential_backoff=exponential_backoff,
                timeout=target_timeout,
            )
            logger.debug("Task registered: %s", func.__name__)
            taskiq_task = self.broker.task(*args, **kwargs)(handler)
            
            # Wrap the kiq method to automatically inject context labels
            original_kiq = taskiq_task.kiq
            
            @functools.wraps(original_kiq)
            def wrapped_kiq(*args: Any, **kwargs: Any) -> Any:
                from eden.context import context_manager
                
                # Get current context snapshot
                snapshot = context_manager.get_context_snapshot()
                
                # Merge into labels
                labels = {}
                for key, value in snapshot.items():
                    if value is not None:
                        labels[key] = str(value)
                
                # Use kicker to send labels properly, rather than polluting kwargs
                return taskiq_task.kicker().with_labels(**labels).kiq(*args, **kwargs)
            
            taskiq_task.kiq = wrapped_kiq

            # ── Idiomatic Eden aliases ────────────────────────────────────
            # .dispatch() — clearer name than .kiq()
            taskiq_task.dispatch = wrapped_kiq

            # .dispatch_after(delay_seconds, *args, **kwargs)
            async def _dispatch_after(delay: int | float, *a: Any, **kw: Any) -> Any:
                """Dispatch this task with a delay (in seconds)."""
                from eden.context import context_manager
                snapshot = context_manager.get_context_snapshot()
                labels = {"delay": str(int(delay))}
                for key, value in snapshot.items():
                    if value is not None:
                        labels[key] = str(value)
                return await taskiq_task.kicker().with_labels(**labels).kiq(*a, **kw)

            taskiq_task.dispatch_after = _dispatch_after

            return taskiq_task

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

    def schedule(
        self,
        cron: str,
    ) -> Callable[[Callable[..., Any]], Any]:
        """Shorthand decorator to register a cron-scheduled periodic task.
        
        This is syntactic sugar for ``@app.task.every(cron="...")``.
        
        Args:
            cron: A standard cron expression (e.g., ``"0 12 * * *"`` for daily at noon)
            
        Example::
        
            @app.task.schedule("0 0 * * *")
            async def nightly_report():
                ...
                
            # Equivalent to:
            @app.task.every(cron="0 0 * * *")
            async def nightly_report():
                ...
        """
        return self.every(cron=cron)

    def _wrap_task_function(
        self, 
        func: Callable[..., Any], 
        max_retries: int, 
        retry_delays: list[int],
        exponential_backoff: bool = True,
        timeout: int = 0,
    ) -> Callable[..., Any]:
        """Wrap a task function to add DI, retry, timeout, signals, and revocation support.
        
        Args:
            func: The original task function
            max_retries: Maximum retry attempts
            retry_delays: Delay schedule per retry attempt (seconds)
            exponential_backoff: Whether to use exponential backoff
            timeout: Execution timeout in seconds (0 = no timeout)
        """

        @functools.wraps(func)
        async def task_handler(*args: Any, context: Any = None, **kwargs: Any) -> Any:
            from eden.dependencies import DependencyResolver
            from eden.context import context_manager, set_request_id, reset_request_id
            import uuid

            # 1. Propagation: Extraction from Taskiq context
            task_id = str(uuid.uuid4())
            tiq_ctx = context or kwargs.pop("context", None)
            snapshot = {}

            if tiq_ctx:
                task_id = getattr(tiq_ctx, "task_id", task_id)
                # Labels carry the whole propagated context snapshot
                snapshot = getattr(tiq_ctx, "labels", {})

            # 2. Check revocation before executing
            if await self.is_revoked(task_id):
                logger.info("Task '%s' (%s) was revoked — skipping execution.", func.__name__, task_id)
                revoked_info = TaskResult(
                    task_id=task_id,
                    task_name=func.__name__,
                    status="revoked",
                    status_message="Task was revoked before execution",
                    completed_at=datetime.now(timezone.utc),
                )
                if self._result_backend:
                    await self._result_backend.store_result(task_id, revoked_info)
                return None

            # Use DependencyResolver with current app instance
            resolver = DependencyResolver()
            # Merge explicitly passed kwargs with injected ones
            try:
                dep_kwargs = await resolver.resolve(func, app=self.app)
            except Exception as e:
                logger.error(
                    "Failed to resolve dependencies for task '%s' (%s): %s", 
                    func.__name__, task_id, e
                )
                raise TaskExecutionError(f"DI failure in task {func.__name__}") from e

            final_kwargs = {**dep_kwargs, **kwargs}

            # 3. Fire prerun signal
            await self._fire_signal(self._on_task_prerun, func.__name__, task_id)

            # Execution loop with retries
            attempt = 0
            start_time = datetime.now(timezone.utc)
            
            while True:
                try:
                    with context_manager.baked_context(snapshot):
                        correlation_id = context_manager.get_request_id()
                        user = context_manager.get_user()
                        # Record start for this attempt with identity info
                        logger.info("Executing task '%s' (attempt %d, ID %s, user=%s)", 
                                     func.__name__, attempt, task_id, user)

                        from eden.tasks.context import _CURRENT_TASK_ID, _CURRENT_BROKER
                        _CURRENT_TASK_ID.set(task_id)
                        _CURRENT_BROKER.set(self)

                        # Initial recording as 'running'
                        start_info = TaskResult(
                            task_id=task_id,
                            task_name=func.__name__,
                            status="running",
                            correlation_id=correlation_id,
                            started_at=start_time,
                        )
                        if self._result_backend:
                            await self._result_backend.store_result(task_id, start_info)

                        # Execute with optional timeout
                        if inspect.iscoroutinefunction(func):
                            if timeout and timeout > 0:
                                try:
                                    res = await asyncio.wait_for(
                                        func(*args, **final_kwargs),
                                        timeout=timeout
                                    )
                                except asyncio.TimeoutError:
                                    raise TaskExecutionError(
                                        f"Task '{func.__name__}' exceeded timeout of {timeout}s"
                                    )
                            else:
                                res = await func(*args, **final_kwargs)
                        else:
                            res = func(*args, **final_kwargs)
                            
                        # Success recording
                        success_info = TaskResult(
                            task_id=task_id,
                            task_name=func.__name__,
                            status="success",
                            result=res,
                            progress=100.0,
                            status_message="Completed",
                            retries=attempt,
                            correlation_id=correlation_id,
                            started_at=start_time,
                            completed_at=datetime.now(timezone.utc),
                        )
                        if self._result_backend:
                            await self._result_backend.store_result(task_id, success_info)

                        # Fire success + postrun signals
                        await self._fire_signal(self._on_task_success, func.__name__, task_id, res)
                        await self._fire_signal(self._on_task_postrun, func.__name__, task_id, "success")
                        return res

                except Exception as e:
                    logger.debug("Task '%s' attempt %d error: %s", func.__name__, attempt, e)
                    attempt += 1
                    if attempt > max_retries:
                        logger.error(
                            "Task '%s' (%s) failed after %d retries: %s", 
                            func.__name__, task_id, max_retries, str(e),
                            exc_info=True
                        )

                        # Record result as dead_letter
                        error_info = TaskResult(
                            task_id=task_id,
                            task_name=func.__name__,
                            status="dead_letter",
                            error=str(e),
                            error_traceback=traceback.format_exc(),
                            retries=attempt - 1,
                            correlation_id=correlation_id,
                            started_at=start_time,
                            completed_at=datetime.now(timezone.utc),
                        )
                        if self._result_backend:
                            await self._result_backend.store_result(task_id, error_info)

                        # Fire failure + postrun signals
                        await self._fire_signal(self._on_task_failure, func.__name__, task_id, e)
                        await self._fire_signal(self._on_task_postrun, func.__name__, task_id, "dead_letter")

                        raise MaxRetriesExceeded(
                            f"Task {func.__name__} failed after {max_retries} retries"
                        ) from e

                    # Record intermediate failure status
                    retry_info = TaskResult(
                        task_id=task_id,
                        task_name=func.__name__,
                        status="failed",
                        error=str(e),
                        retries=attempt - 1,
                        correlation_id=correlation_id,
                        started_at=start_time,
                    )
                    if self._result_backend:
                        await self._result_backend.store_result(task_id, retry_info)

                    # Revised Exponential backoff logic
                    idx = attempt - 1
                    if idx < len(retry_delays):
                        delay = retry_delays[idx]
                    else:
                        last_delay = retry_delays[-1] if retry_delays else 1
                        if exponential_backoff:
                            growth = idx - len(retry_delays) + 1
                            delay = last_delay * (2 ** growth)
                        else:
                            delay = last_delay

                    logger.warning(
                        "Task '%s' (%s) failed (attempt %d). Retrying in %ds... (Correlation: %s)",
                        func.__name__,
                        task_id,
                        attempt,
                        delay,
                        correlation_id
                    )
                    await asyncio.sleep(delay)

        return task_handler

    async def defer(self, task: Any, *args: Any, **kwargs: Any) -> Any:
        """Send a task to the broker queue immediately."""
        if not self._startup_complete:
            raise BrokerNotInitialized("Broker not started.")
        return await task.kiq(*args, **kwargs)

    async def schedule(self, task: Any, delay: int | float, *args: Any, **kwargs: Any) -> Any:
        """Send a task to the queue with a delay.
        
        Args:
            task: A task object registered via @app.task()
            delay: Delay in seconds before the task executes
            *args: Positional arguments to pass to the task
            **kwargs: Keyword arguments to pass to the task
            
        Returns:
            The kiq result (task handle)
        """
        if not self._startup_complete:
            raise BrokerNotInitialized("Broker not started.")
        # Use kicker().with_labels().kiq() pattern — NOT task.kiq() which dispatches immediately
        return await task.kicker().with_labels(delay=int(delay)).kiq(*args, **kwargs)

    async def startup(self) -> None:
        """Start the broker and all registered periodic tasks."""
        if self._running:
            return

        logger.info("Starting Eden Task Broker...")
        await self.broker.startup()

        # Register result cleanup as a periodic task if not already there
        async def _cleanup_results_task():
            await self._result_backend.cleanup_expired()
        
        # We don't use @self.every because we want to start it immediately 
        # as part of the internal lifecycle
        cleanup_pt = PeriodicTask(_cleanup_results_task, self, hours=1)
        self._periodic.append(cleanup_pt)

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
