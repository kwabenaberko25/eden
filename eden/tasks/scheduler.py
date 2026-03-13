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

from typing import Callable, Optional, List
from datetime import datetime, timedelta
import re
import asyncio


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
                    # Range with step: "10-50/5"
                    start, end = map(int, range_part.split("-"))
                    values.update(range(start, end + 1, step))
            
            elif "-" in part:
                # Ranges: "1-5"
                start, end = part.split("-")
                start = self._resolve_name(field_index, start)
                end = self._resolve_name(field_index, end)
                values.update(range(start, end + 1))
            
            else:
                # Single value
                values.add(self._resolve_name(field_index, part))
        
        return values
    
    def _resolve_name(self, field_index: int, value: str) -> int:
        """Resolve month/day names to numbers."""
        if field_index in self.NAMES:
            return self.NAMES[field_index].get(value.lower(), int(value))
        return int(value)
    
    def matches(self, dt: Optional[datetime] = None) -> bool:
        """Check if datetime matches this cron expression."""
        if dt is None:
            dt = datetime.now()
        
        # Check each field
        return (
            dt.minute in self.fields[self.MINUTE] and
            dt.hour in self.fields[self.HOUR] and
            (dt.day in self.fields[self.DAY_OF_MONTH] or
             dt.weekday() + 1 % 7 in self.fields[self.DAY_OF_WEEK]) and
            dt.month in self.fields[self.MONTH]
        )
    
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
        scheduler = TaskScheduler()
        
        @scheduler.schedule("0 12 * * *")
        async def daily_task():
            pass
        
        await scheduler.start()  # Start the scheduler
    """
    
    def __init__(self):
        """Initialize task scheduler."""
        self.tasks: List[tuple[CronExpression, Callable, str]] = []
        self._running = False
    
    def schedule(self, cron_expr: str):
        """Decorator to schedule a task."""
        def decorator(func: Callable) -> Callable:
            try:
                cron = CronExpression(cron_expr)
                self.tasks.append((cron, func, cron_expr))
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
    
    async def start(self) -> None:
        """Start the scheduler (runs until stop() called)."""
        self._running = True
        print(f"✓ Task scheduler started ({len(self.tasks)} tasks)")
        
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
            print(f"✗ Scheduler error: {e}")
        
        finally:
            self._running = False
            print("✓ Task scheduler stopped")
    
    async def _run_task(self, func: Callable, name: str) -> None:
        """Run a scheduled task with error handling."""
        try:
            print(f"► Running scheduled task: {name}")
            result = func()
            
            # Handle async functions
            if hasattr(result, '__await__'):
                await result
            
            print(f"✓ Task completed: {name}")
        
        except Exception as e:
            print(f"✗ Task failed ({name}): {e}")
    
    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
    
    def list_tasks(self) -> list[dict]:
        """Get list of scheduled tasks."""
        return [
            {
                "name": name,
                "cron": cron.expression,
                "next_run": cron.next_run().isoformat(),
            }
            for cron, func, name in self.tasks
        ]


# Global scheduler instance
scheduler = TaskScheduler()
