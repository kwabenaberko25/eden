"""
Eden — Task Queue Integration

Provides EdenBroker: a wrapper around Taskiq for background tasks
and periodic / cron-style scheduling.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any, TypeVar

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

logger = logging.getLogger("eden.tasks")

T = TypeVar("T")


# ── Periodic Task Descriptor ──────────────────────────────────────────────────

class PeriodicTask:
    """
    Holds the schedule config for a periodic task registered via .every().
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
        self.func = func
        self.task = func  # Alias for tests
        self.cron = cron
        self.seconds = seconds
        self.minutes = minutes
        self.hours = hours
        self._interval_seconds: float = seconds + minutes * 60 + hours * 3600
        self._task_handle: asyncio.Task | None = None

    @property
    def interval(self) -> float:
        """Total interval in seconds (0 if cron-based)."""
        return self._interval_seconds

    async def _run_loop(self) -> None:
        """Run the task repeatedly at the configured interval."""
        while True:
            await asyncio.sleep(self._interval_seconds)
            try:
                result = self.func()
                if asyncio.iscoroutine(result):
                    await result
            except Exception as exc:
                logger.error(
                    "Periodic task '%s' raised an exception: %s",
                    self.func.__name__,
                    exc,
                    exc_info=True,
                )

    def start(self) -> None:
        """Schedule the task loop in the current event loop."""
        if self._interval_seconds <= 0:
            logger.warning(
                "Periodic task '%s' has no interval configured — skipping.",
                self.func.__name__,
            )
            return
        self._task_handle = asyncio.ensure_future(self._run_loop())
        logger.info(
            "Periodic task '%s' started (every %.1f seconds).",
            self.func.__name__,
            self._interval_seconds,
        )

    def stop(self) -> None:
        """Cancel the running task loop."""
        if self._task_handle and not self._task_handle.done():
            self._task_handle.cancel()
            logger.info("Periodic task '%s' stopped.", self.func.__name__)


# ── EdenBroker ────────────────────────────────────────────────────────────────

class EdenBroker:
    """
    Native Eden wrapper for the Taskiq broker.

    Supports:
        - @app.task()            → Background task (one-shot)
        - @app.task.every(...)   → Periodic/repeating task
        - app.task.defer(fn, …)  → Send a task to the queue immediately
        - app.task.schedule(fn, delay, …) → Send with a delay label

    Usage::

        # One-shot background task
        @app.task()
        async def send_email(to: str): ...

        # Periodic task — every 5 minutes
        @app.task.every(minutes=5)
        async def refresh_cache(): ...

        # Periodic task — every 30 seconds
        @app.task.every(seconds=30)
        async def heartbeat(): ...
    """

    def __init__(self, broker: AsyncBroker) -> None:
        self.broker = broker
        self._periodic: list[PeriodicTask] = []

    @property
    def periodic_tasks(self) -> list[PeriodicTask]:
        """Backwards compatibility for tests."""
        return self._periodic

    # ── Core decorator ────────────────────────────────────────────────────────

    def __call__(self, *args: Any, **kwargs: Any) -> Callable[[Callable[..., Any]], Any]:
        """Alias so @app.task() works like @app.task.task()."""
        return self.task(*args, **kwargs)

    def task(self, *args: Any, **kwargs: Any) -> Any:
        """
        Decorator to register a background task.

        Usage::
            @app.task()
            async def process(user_id: int): ...

            # Then trigger it:
            await process.kiq(42)
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

        The task is invoked in the current event loop at the configured interval.
        For production multi-process setups, use a Redis broker + Taskiq Scheduler.

        Usage::
            @app.task.every(minutes=5)
            async def refresh_cache():
                await Cache.invalidate_all()

            @app.task.every(hours=1)
            async def send_digest():
                await send_daily_digest()

            @app.task.every(seconds=30)
            async def heartbeat():
                logger.info("alive")
        """
        def decorator(func: Callable[..., Any]) -> Any:
            # Wrap as a task first so it has .kiq() and proper taskiq registration
            task_func = self.task()(func)
            
            periodic = PeriodicTask(
                task_func,
                seconds=seconds,
                minutes=minutes,
                hours=hours,
                cron=cron,
            )
            self._periodic.append(periodic)
            logger.debug(
                "Registered periodic task: '%s' (every %.1fs)",
                func.__name__,
                periodic.interval,
            )
            return task_func

        return decorator

    # ── Queue helpers ─────────────────────────────────────────────────────────

    async def defer(self, task: Any, *args: Any, **kwargs: Any) -> Any:
        """
        Send a task to the broker queue immediately (fire-and-forget).

        Usage::
            await app.task.defer(send_email, to="user@example.com")
        """
        return await task.kiq(*args, **kwargs)

    async def schedule(
        self, task: Any, delay: int | float, *args: Any, **kwargs: Any
    ) -> Any:
        """
        Send a task to the queue with a delay (in seconds).

        Only works when the broker / result backend supports the ``delay`` label
        (e.g. taskiq-redis with Taskiq Scheduler).

        Usage::
            await app.task.schedule(send_reminder, delay=3600, user_id=42)
        """
        kicker = task.kiq(*args, **kwargs)
        if hasattr(kicker, "with_labels"):
            return await kicker.with_labels(delay=int(delay))
        return await kicker

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def startup(self) -> None:
        """Start the broker and all registered periodic tasks."""
        await self.broker.startup()
        for periodic in self._periodic:
            periodic.start()

    async def shutdown(self) -> None:
        """Stop all periodic tasks and shut down the broker."""
        for periodic in self._periodic:
            periodic.stop()
        await self.broker.shutdown()


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
