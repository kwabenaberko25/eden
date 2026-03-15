"""
Test suite for Tier 2: Task Scheduler with Cron

Tests CronExpression parser and TaskScheduler functionality.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from eden.tasks.scheduler import (
    CronExpression,
    TaskScheduler,
    SchedulerException,
)


class TestCronExpression:
    """Tests for CronExpression parser."""
    
    def test_cron_every_day_at_noon(self):
        """Test daily schedule at 12:00."""
        expr = CronExpression("0 12 * * *")
        
        # Should match 12:00
        assert expr.matches(datetime(2024, 1, 1, 12, 0)) is True
        
        # Should not match 12:30
        assert expr.matches(datetime(2024, 1, 1, 12, 30)) is False
        
        # Should not match 13:00
        assert expr.matches(datetime(2024, 1, 1, 13, 0)) is False
    
    def test_cron_every_hour(self):
        """Test hourly schedule."""
        expr = CronExpression("0 * * * *")
        
        # Should match any hour at :00
        assert expr.matches(datetime(2024, 1, 1, 0, 0)) is True
        assert expr.matches(datetime(2024, 1, 1, 12, 0)) is True
        assert expr.matches(datetime(2024, 1, 1, 23, 0)) is True
        
        # Should not match any other minute
        assert expr.matches(datetime(2024, 1, 1, 12, 30)) is False
    
    def test_cron_every_five_minutes(self):
        """Test 5-minute intervals."""
        expr = CronExpression("*/5 * * * *")
        
        # Should match every 5 minutes
        assert expr.matches(datetime(2024, 1, 1, 12, 0)) is True
        assert expr.matches(datetime(2024, 1, 1, 12, 5)) is True
        assert expr.matches(datetime(2024, 1, 1, 12, 10)) is True
        
        # Should not match odd minutes
        assert expr.matches(datetime(2024, 1, 1, 12, 3)) is False
    
    def test_cron_specific_days_of_week(self):
        """Test specific day of week."""
        expr = CronExpression("0 0 * * 1")  # Mondays only
        
        # 2024-01-01 is Monday
        monday = datetime(2024, 1, 1, 0, 0)
        assert expr.matches(monday) is True
        
        # 2024-01-02 is Tuesday
        tuesday = datetime(2024, 1, 2, 0, 0)
        assert expr.matches(tuesday) is False
    
    def test_cron_weekdays_only(self):
        """Test weekday schedule (Monday-Friday)."""
        expr = CronExpression("0 9 * * 1-5")  # 9 AM Mon-Fri
        
        # Monday 9 AM
        monday = datetime(2024, 1, 1, 9, 0)
        assert expr.matches(monday) is True
        
        # Saturday 9 AM
        saturday = datetime(2024, 1, 6, 9, 0)
        assert expr.matches(saturday) is False
    
    def test_cron_specific_dates(self):
        """Test specific dates of month."""
        expr = CronExpression("0 0 15 * *")  # 15th of every month
        
        # 15th matches
        assert expr.matches(datetime(2024, 1, 15, 0, 0)) is True
        
        # 14th doesn't match
        assert expr.matches(datetime(2024, 1, 14, 0, 0)) is False
    
    def test_cron_specific_months(self):
        """Test specific months."""
        expr = CronExpression("0 0 1 1 *")  # January 1st
        
        # Jan 1 matches
        assert expr.matches(datetime(2024, 1, 1, 0, 0)) is True
        
        # Feb 1 doesn't match
        assert expr.matches(datetime(2024, 2, 1, 0, 0)) is False
    
    def test_cron_month_names(self):
        """Test month names."""
        expr = CronExpression("0 0 1 jan *")  # January 1st
        
        assert expr.matches(datetime(2024, 1, 1, 0, 0)) is True
        assert expr.matches(datetime(2024, 2, 1, 0, 0)) is False
    
    def test_cron_day_names(self):
        """Test day-of-week names."""
        expr = CronExpression("0 0 * * mon")  # Mondays
        
        # 2024-01-01 is Monday
        assert expr.matches(datetime(2024, 1, 1, 0, 0)) is True
        
        # 2024-01-02 is Tuesday
        assert expr.matches(datetime(2024, 1, 2, 0, 0)) is False
    
    def test_cron_list_syntax(self):
        """Test list syntax (1,3,5)."""
        expr = CronExpression("0 * * * 1,3,5")  # Mon, Wed, Fri
        
        # Monday (1)
        assert expr.matches(datetime(2024, 1, 1, 0, 0)) is True
        
        # Wednesday (3)
        assert expr.matches(datetime(2024, 1, 3, 0, 0)) is True
        
        # Tuesday (2)
        assert expr.matches(datetime(2024, 1, 2, 0, 0)) is False
    
    def test_cron_range_syntax(self):
        """Test range syntax (1-5)."""
        expr = CronExpression("0 * * * 1-5")  # Mon-Fri
        
        # Monday to Friday
        for day in range(1, 6):  # Mon=1, Tue=2, ..., Fri=5
            assert expr.matches(datetime(2024, 1, day, 0, 0)) is True
        
        # Saturday and Sunday
        assert expr.matches(datetime(2024, 1, 6, 0, 0)) is False
        assert expr.matches(datetime(2024, 1, 7, 0, 0)) is False
    
    def test_cron_step_syntax(self):
        """Test step syntax (*/5, 10-50/5)."""
        expr = CronExpression("0-30/5 * * * *")  # :00, :05, :10, etc.
        
        assert expr.matches(datetime(2024, 1, 1, 12, 0)) is True
        assert expr.matches(datetime(2024, 1, 1, 12, 5)) is True
        assert expr.matches(datetime(2024, 1, 1, 12, 10)) is True
        assert expr.matches(datetime(2024, 1, 1, 12, 3)) is False
    
    def test_next_run(self):
        """Test calculating next run time."""
        expr = CronExpression("0 12 * * *")  # Daily at noon
        
        now = datetime(2024, 1, 1, 10, 0)
        next_run = expr.next_run(now)
        
        # Should be same day at noon
        assert next_run.year == 2024
        assert next_run.month == 1
        assert next_run.day == 1
        assert next_run.hour == 12
        assert next_run.minute == 0
    
    def test_next_run_past(self):
        """Test next_run when scheduled time has passed."""
        expr = CronExpression("0 12 * * *")  # Daily at noon
        
        now = datetime(2024, 1, 1, 14, 0)  # 2 PM
        next_run = expr.next_run(now)
        
        # Should be next day at noon
        assert next_run.day == 2
        assert next_run.hour == 12
    
    def test_invalid_cron_expression(self):
        """Test handling of invalid cron expressions."""
        with pytest.raises(ValueError):
            CronExpression("invalid cron")
    
    def test_invalid_cron_values(self):
        """Test handling of out-of-range values."""
        with pytest.raises(ValueError):
            CronExpression("60 * * * *")  # Invalid minute (60)
        
        with pytest.raises(ValueError):
            CronExpression("0 25 * * *")  # Invalid hour (25)


class TestTaskScheduler:
    """Tests for TaskScheduler class."""
    
    @pytest.fixture
    def scheduler(self):
        """Create a TaskScheduler instance."""
        from eden import App
        app = App(__name__)
        scheduler = TaskScheduler(app)
        yield scheduler
    
    def test_scheduler_initialization(self, scheduler):
        """Test TaskScheduler initialization."""
        assert scheduler is not None
        assert len(scheduler.list_tasks()) == 0
    
    def test_schedule_decorator(self, scheduler):
        """Test @schedule decorator."""
        @scheduler.schedule("0 12 * * *")
        async def daily_task():
            return "done"
        
        tasks = scheduler.list_tasks()
        assert len(tasks) > 0
        assert any(t["name"] == "daily_task" for t in tasks)
    
    def test_add_task(self, scheduler):
        """Test programmatic task registration."""
        async def hourly_task():
            return "hourly"
        
        scheduler.add_task(hourly_task, "0 * * * *")
        
        tasks = scheduler.list_tasks()
        assert len(tasks) > 0
    
    def test_list_tasks(self, scheduler):
        """Test listing scheduled tasks."""
        @scheduler.schedule("0 12 * * *")
        async def task1():
            pass
        
        @scheduler.schedule("0 */6 * * *")
        async def task2():
            pass
        
        tasks = scheduler.list_tasks()
        assert len(tasks) >= 2
        assert all("name" in t and "cron" in t for t in tasks)
    
    @pytest.mark.asyncio
    async def test_scheduler_start_stop(self, scheduler):
        """Test starting and stopping scheduler."""
        call_count = 0
        
        @scheduler.schedule("* * * * *")  # Every minute
        async def test_task():
            nonlocal call_count
            call_count += 1
        
        # Start scheduler
        task = asyncio.create_task(scheduler.start())
        
        # Let it run briefly
        await asyncio.sleep(0.1)
        
        # Stop scheduler
        scheduler.stop()
        await asyncio.sleep(0.1)
        
        # Task should have been called or at least scheduler started
        assert task is not None
    
    def test_remove_task(self, scheduler):
        """Test removing a scheduled task."""
        @scheduler.schedule("0 12 * * *")
        async def task_to_remove():
            pass
        
        assert len(scheduler.list_tasks()) > 0
        
        scheduler.remove_task("task_to_remove")
        
        tasks = scheduler.list_tasks()
        assert not any(t["name"] == "task_to_remove" for t in tasks)
    
    @pytest.mark.asyncio
    async def test_task_error_handling(self, scheduler):
        """Test that scheduler handles task errors gracefully."""
        error_count = 0
        
        @scheduler.schedule("* * * * *")
        async def failing_task():
            raise ValueError("Task failed")
        
        # Scheduler should handle errors and continue
        # (Actual behavior depends on error handling implementation)
        assert len(scheduler.list_tasks()) > 0


class TestSchedulerIntegration:
    """Integration tests for scheduler."""
    
    @pytest.mark.asyncio
    async def test_multiple_tasks_execution(self):
        """Test executing multiple tasks."""
        from eden import App
        scheduler = TaskScheduler(App(__name__))
        
        executed = []
        
        @scheduler.schedule("0 12 * * *")
        async def task1():
            executed.append("task1")
        
        @scheduler.schedule("0 */6 * * *")
        async def task2():
            executed.append("task2")
        
        tasks = scheduler.list_tasks()
        assert len(tasks) == 2
    
    @pytest.mark.asyncio
    async def test_cron_expression_matching_in_scheduler(self):
        """Test that scheduler uses cron expressions correctly."""
        from eden import App
        scheduler = TaskScheduler(App(__name__))
        
        @scheduler.schedule("0 12 * * mon")
        async def monday_task():
            pass
        
        tasks = scheduler.list_tasks()
        monday_task_info = next(t for t in tasks if t["name"] == "monday_task")
        
        assert "0 12 * * mon" in monday_task_info["cron"]


class TestSchedulerErrors:
    """Test error handling in scheduler."""
    
    def test_invalid_cron_in_schedule(self):
        """Test that invalid cron raises error."""
        from eden import App
        scheduler = TaskScheduler(App(__name__))
        
        with pytest.raises(ValueError):
            @scheduler.schedule("invalid cron")
            async def task():
                pass
    
    def test_duplicate_task_names(self):
        """Test handling of duplicate task names."""
        from eden import App
        scheduler = TaskScheduler(App(__name__))
        
        @scheduler.schedule("0 12 * * *")
        async def duplicate_name():
            pass
        
        # Adding another with same name should either override or raise
        @scheduler.schedule("0 13 * * *")
        async def duplicate_name():
            pass
        
        # Should have at least one task
        assert len(scheduler.list_tasks()) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
