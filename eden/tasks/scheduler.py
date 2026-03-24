"""
Eden Task Scheduling - Cron Support

Extends eden/tasks.py with cron expression support for scheduled jobs.

Usage:
    @app.schedule("0 12 * * *")  # Every day at noon
    async def daily_cleanup():
        await PasswordResetToken.delete_expired()
    
    # Or register programmatically
    app.scheduler.schedule(daily_cleanup, "0 */6 * * *")  # Every 6 hours
"""

import logging
from typing import Callable, Optional, List, Any
from datetime import datetime, timedelta
import re
import asyncio

from eden.tasks.exceptions import SchedulerException

logger = logging.getLogger("eden.tasks.scheduler")


class CronExpression:
    """
    Parse and validate cron expressions.
    Format: minute hour day_of_month month day_of_week
    
    Examples:
        "0 12 * * *"        - Every day at 12:00 (noon)
        "0 */6 * * *"       - Every 6 hours
        "30 2 * * 0"        - Every Sunday at 2:30 AM
        "0 0 1 * *"         - First day of every month at midnight
        "0 9 * * 1-5"       - Weekdays at 9:00 AM
    """
    
    MINUTE = 0      # 0-59
    HOUR = 1        # 0-23
    DAY_OF_MONTH = 2  # 1-31
    MONTH = 3       # 1-12
    DAY_OF_WEEK = 4  # 0-6 (0=Sunday)
    
    RANGES = {
        MINUTE: (0, 59),
        HOUR: (0, 23),
        DAY_OF_MONTH: (1, 31),
        MONTH: (1, 12),
        DAY_OF_WEEK: (0, 6),
    }
    
    NAMES = {
        MONTH: {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
        },
        DAY_OF_WEEK: {
            "sun": 0, "mon": 1, "tue": 2, "wed": 3,
            "thu": 4, "fri": 5, "sat": 6
        }
    }
    
    def __init__(self, expression: str):
        """Parse cron expression."""
        parts = expression.strip().split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: {expression}")
        
        self.expression = expression
        self.parts = parts
        self._is_wildcard = [part == "*" for part in parts]
        self.fields = [self._parse_field(i, parts[i]) for i in range(5)]
    
    def _parse_field(self, field_index: int, field: str) -> set[int]:
        """Parse a single cron field."""
        if field == "*":
            min_val, max_val = self.RANGES[field_index]
            return set(range(min_val, max_val + 1))
        
        values = set()
        
        # Handle ranges and lists: "1-5", "1,3,5", "*/2"
        for part in field.split(","):
            if "/" in part:
                # Step values: "*/5" or "10-50/5"
                range_part, step = part.split("/")
                step = int(step)
                
                if range_part == "*":
                    min_val, max_val = self.RANGES[field_index]
                    values.update(range(min_val, max_val + 1, step))
                else:
                    # Range with step: "10-50/5" or "mon-fri/2"
                    start, end = range_part.split("-")
                    start = self._resolve_name(field_index, start)
                    end = self._resolve_name(field_index, end)
                    values.update(range(start, end + 1, step))
            
            elif "-" in part:
                # Ranges: "1-5"
                start, end = part.split("-")
                start = self._resolve_name(field_index, start)
                end = self._resolve_name(field_index, end)
                values.update(range(start, end + 1))
            
            else:
                # Single value
                val = self._resolve_name(field_index, part)
                values.add(val)
        
        # Validate values are within range
        min_range, max_range = self.RANGES[field_index]
        for val in values:
            if not (min_range <= val <= max_range):
                raise ValueError(
                    f"Value {val} out of range ({min_range}-{max_range}) for field {field_index}"
                )
        
        return values
    
    def _resolve_name(self, field_index: int, value: str) -> int:
        """Resolve month/day names to numbers."""
        if field_index in self.NAMES:
            val_lower = value.lower()
            if val_lower in self.NAMES[field_index]:
                return self.NAMES[field_index][val_lower]
        return int(value)
    
    def matches(self, dt: Optional[datetime] = None) -> bool:
        """Check if datetime matches this cron expression."""
        if dt is None:
            dt = datetime.now()
        
        # Check each field
        # Note: day of month and day of week have special "OR" relationship 
        # when both are restricted.
        dom_restricted = not self._is_wildcard[self.DAY_OF_MONTH]
        dow_restricted = not self._is_wildcard[self.DAY_OF_WEEK]
        
        minute_match = dt.minute in self.fields[self.MINUTE]
        hour_match = dt.hour in self.fields[self.HOUR]
        month_match = dt.month in self.fields[self.MONTH]
        
        if dom_restricted and dow_restricted:
            day_match = (
                dt.day in self.fields[self.DAY_OF_MONTH] or
                (dt.weekday() + 1) % 7 in self.fields[self.DAY_OF_WEEK]
            )
        else:
            day_match = (
                dt.day in self.fields[self.DAY_OF_MONTH] and
                (dt.weekday() + 1) % 7 in self.fields[self.DAY_OF_WEEK]
            )
            
        return minute_match and hour_match and month_match and day_match
    
    def next_run(self, after: Optional[datetime] = None) -> datetime:
        """Calculate next execution time."""
        if after is None:
            after = datetime.now()
        
        # Start from next minute
        current = after.replace(second=0, microsecond=0) + timedelta(minutes=1)
        
        # Search up to 4 years in future
        end = current + timedelta(days=4*365)
        
        while current < end:
            if self.matches(current):
                return current
            current += timedelta(minutes=1)
        
        raise ValueError("Could not find next run time for cron expression")


class TaskScheduler:
    """
    Schedule async tasks using cron expressions.
    
    Usage:
        scheduler = TaskScheduler(app)
        
        @scheduler.schedule("0 12 * * *")
        async def daily_task():
            pass
        
        await scheduler.start()  # Start the scheduler
    """
    
    def __init__(self, app: Optional[Any] = None):
        """
        Initialize task scheduler.
        
        Args:
            app: Optional Eden application instance
        """
        self.app = app
        self.tasks: List[tuple[CronExpression, Callable, str]] = []
        self._running = False
    
    def schedule(self, cron_expr: str):
        """Decorator to schedule a task."""
        def decorator(func: Callable) -> Callable:
            try:
                cron = CronExpression(cron_expr)
                self.tasks.append((cron, func, func.__name__))
                return func
            except ValueError as e:
                raise ValueError(f"Invalid cron expression in @schedule: {e}")
        
        return decorator
    
    def add_task(
        self,
        func: Callable,
        cron_expr: str,
        name: Optional[str] = None,
    ) -> None:
        """Register a task programmatically."""
        try:
            cron = CronExpression(cron_expr)
            self.tasks.append((cron, func, name or func.__name__))
        except ValueError as e:
            raise ValueError(f"Invalid cron expression: {e}")

    def remove_task(self, name: str) -> None:
        """Remove a task by name."""
        self.tasks = [t for t in self.tasks if t[2] != name]
    
    async def start(self) -> None:
        """Start the scheduler (runs until stop() called)."""
        self._running = True
        logger.info("Task scheduler started (%d tasks)", len(self.tasks))
        
        last_minute = None
        
        try:
            while self._running:
                now = datetime.now()
                
                # Only check once per minute
                if now.minute != last_minute:
                    last_minute = now.minute
                    
                    # Check all tasks
                    for cron, func, name in self.tasks:
                        if cron.matches(now):
                            # Run task concurrently
                            asyncio.create_task(self._run_task(func, name))
                
                # Sleep until next minute
                await asyncio.sleep(10)
        
        except Exception as e:
            logger.error("Scheduler error: %s", e, exc_info=True)
        
        finally:
            self._running = False
            logger.info("Task scheduler stopped")
    
    async def _run_task(self, func: Callable, name: str) -> None:
        """Run a scheduled task with error handling."""
        try:
            logger.info("Running scheduled task: %s", name)
            result = func()
            
            # Handle async functions
            if hasattr(result, '__await__'):
                await result
            
            logger.info("Task completed: %s", name)
        
        except Exception as e:
            logger.error("Task failed (%s): %s", name, e, exc_info=True)
    
    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
    
    def list_tasks(self) -> list[dict]:
        """Get list of scheduled tasks."""
        results = []
        for cron, func, name in self.tasks:
            try:
                next_run = cron.next_run().isoformat()
            except ValueError:
                next_run = None
                
            results.append({
                "name": name,
                "cron": cron.expression,
                "next_run": next_run,
            })
        return results


# Global scheduler instance
scheduler = TaskScheduler()
