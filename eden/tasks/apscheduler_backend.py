"""
APScheduler Task Scheduling Backend

Provides APScheduler-based scheduling for production multi-process task execution.
Handles both interval-based and cron-based scheduling with timezone support.

This backend is recommended for production deployments where tasks need to run
across multiple worker processes with guaranteed execution windows.

Usage::

    from eden.tasks.apscheduler_backend import APSchedulerBackend
    
    backend = APSchedulerBackend(timezone="UTC")
    
    @backend.schedule_every(seconds=30)
    async def heartbeat():
        logger.info("Still alive")
    
    await backend.start()
"""

import logging
from typing import Optional, Callable, Any
from datetime import datetime, timezone

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    HAS_APSCHEDULER = True
except ImportError:
    HAS_APSCHEDULER = False
    AsyncIOScheduler = None
    CronTrigger = None
    IntervalTrigger = None

from eden.tasks.exceptions import SchedulerError, InvalidCronExpression

logger = logging.getLogger("eden.tasks.scheduler")


class APSchedulerBackend:
    """
    Production scheduler using APScheduler with asyncio backend.

    Features:
        - Interval-based scheduling (every N seconds/minutes/hours)
        - Cron-expression scheduling (e.g., "0 12 * * *")
        - Timezone support
        - Job persistence and state tracking
        - Manual job listing and management

    Example::

        backend = APSchedulerBackend()
        
        @backend.schedule_every(minutes=5)
        async def refresh_cache():
            pass
        
        await backend.start()
    """

    def __init__(self, timezone: Optional[str] = None) -> None:
        """
        Initialize the APScheduler backend.

        Args:
            timezone: Timezone string (e.g., "UTC", "America/New_York")
        """
        if not HAS_APSCHEDULER:
            raise ImportError(
                "APScheduler is required. Install with: pip install apscheduler"
            )

        self.scheduler = AsyncIOScheduler(timezone=timezone or "UTC")
        self._running = False

    async def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            logger.warning("Scheduler already running")
            return

        self.scheduler.start()
        self._running = True
        logger.info("APScheduler started (%d jobs)", len(self.scheduler.get_jobs()))

    async def shutdown(self) -> None:
        """Stop the scheduler."""
        if not self._running:
            return

        self.scheduler.shutdown()
        self._running = False
        logger.info("APScheduler shut down")

    def schedule_every(
        self,
        *,
        seconds: Optional[float] = None,
        minutes: Optional[float] = None,
        hours: Optional[float] = None,
    ) -> Callable:
        """Register an interval-based scheduled task."""
        def decorator(func: Callable) -> Callable:
            try:
                trigger = IntervalTrigger(
                    seconds=seconds,
                    minutes=minutes,
                    hours=hours,
                )
                self.scheduler.add_job(
                    func,
                    trigger=trigger,
                    id=func.__name__,
                    replace_existing=True,
                )
                logger.debug(
                    "Scheduled task '%s' with interval (s=%s, m=%s, h=%s)",
                    func.__name__,
                    seconds,
                    minutes,
                    hours,
                )
            except Exception as e:
                raise SchedulerError(f"Failed to schedule '{func.__name__}': {e}")
            return func
        return decorator

    def schedule_cron(self, cron_expr: str) -> Callable:
        """Register a cron-based scheduled task."""
        def decorator(func: Callable) -> Callable:
            try:
                trigger = CronTrigger.from_crontab(cron_expr)
                self.scheduler.add_job(
                    func,
                    trigger=trigger,
                    id=f"{func.__name__}:{cron_expr}",
                    replace_existing=True,
                )
                logger.debug(
                    "Scheduled task '%s' with cron '%s'",
                    func.__name__,
                    cron_expr,
                )
            except Exception as e:
                raise InvalidCronExpression(
                    cron_expr,
                    f"Failed to create cron trigger: {e}",
                )
            return func
        return decorator

    def list_jobs(self) -> list[dict[str, Any]]:
        """Get list of all scheduled jobs."""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "func": str(job.func),
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            })
        return jobs

    def remove_job(self, job_id: str) -> bool:
        """
        Remove a scheduled job by ID.

        Returns:
            True if job was removed, False if not found
        """
        try:
            self.scheduler.remove_job(job_id)
            logger.info("Removed job: %s", job_id)
            return True
        except Exception:
            return False

    def pause_job(self, job_id: str) -> bool:
        """Pause a scheduled job."""
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                job.pause()
                logger.info("Paused job: %s", job_id)
                return True
            return False
        except Exception:
            return False

    def resume_job(self, job_id: str) -> bool:
        """Resume a paused scheduled job."""
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                job.resume()
                logger.info("Resumed job: %s", job_id)
                return True
            return False
        except Exception:
            return False
