"""
Integration tests for APScheduler, Analytics, Feature Flags, and Cursor Pagination.

Tests real-world usage patterns and interactions between features.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal

from eden.apscheduler_backend import (
    APSchedulerBackend, SchedulerConfig, JobDefinition, MemoryJobStore
)
from eden.analytics import (
    AnalyticsManager, NoOpProvider, GoogleAnalyticsProvider,
    SegmentProvider, MixpanelProvider
)
from eden.flags import FlagManager, FlagContext, FlagStrategy
from eden.db.cursor import CursorPaginator, paginate


# ============================================================================
# APScheduler Tests
# ============================================================================

class TestAPSchedulerBackend:
    """Test APScheduler integration."""
    
    @pytest.fixture
    async def scheduler(self):
        config = SchedulerConfig(max_workers=2)
        scheduler = APSchedulerBackend(config=config)
        yield scheduler
        await scheduler.stop()
    
    async def test_scheduler_lifecycle(self, scheduler):
        """Test start/stop lifecycle."""
        assert not scheduler.running
        await scheduler.start()
        assert scheduler.running
        await asyncio.sleep(0.1)
        await scheduler.stop()
        assert not scheduler.running
    
    async def test_add_job(self, scheduler):
        """Test adding a job."""
        async def dummy_task():
            pass
        
        job = await scheduler.add_job(dummy_task, trigger="interval", seconds=60)
        assert job.id is not None
        assert job.trigger == "interval"
        
        retrieved = await scheduler.get_job(job.id)
        assert retrieved is not None
        assert retrieved.func == dummy_task
    
    async def test_job_execution_interval(self, scheduler):
        """Test interval job execution."""
        executed = []
        
        async def task():
            executed.append(datetime.now())
        
        await scheduler.start()
        
        job = await scheduler.add_job(task, trigger="interval", interval_seconds=1)
        
        # Give scheduler time to execute
        await asyncio.sleep(2.5)
        await scheduler.stop()
        
        # Should have executed at least once
        assert len(executed) >= 1
    
    async def test_remove_job(self, scheduler):
        """Test removing a job."""
        async def dummy_task():
            pass
        
        job = await scheduler.add_job(dummy_task, trigger="interval", seconds=60)
        await scheduler.remove_job(job.id)
        
        retrieved = await scheduler.get_job(job.id)
        assert retrieved is None
    
    async def test_job_with_kwargs(self, scheduler):
        """Test job with keyword arguments."""
        results = []
        
        async def task(name, value):
            results.append({"name": name, "value": value})
        
        await scheduler.add_job(
            task,
            trigger="interval",
            seconds=1,
            kwargs={"name": "test", "value": 42}
        )
        
        await scheduler.start()
        await asyncio.sleep(1.5)
        await scheduler.stop()
        
        assert len(results) > 0
        assert results[0] == {"name": "test", "value": 42}
    
    async def test_multiple_jobs(self, scheduler):
        """Test multiple jobs running concurrently."""
        counter = {"a": 0, "b": 0}
        
        async def task_a():
            counter["a"] += 1
        
        async def task_b():
            counter["b"] += 1
        
        await scheduler.add_job(task_a, trigger="interval", interval_seconds=1)
        await scheduler.add_job(task_b, trigger="interval", interval_seconds=1)
        
        await scheduler.start()
        await asyncio.sleep(1.5)
        await scheduler.stop()
        
        assert counter["a"] > 0
        assert counter["b"] > 0
    
    async def test_get_all_jobs(self, scheduler):
        """Test retrieving all jobs."""
        async def task1():
            pass
        
        async def task2():
            pass
        
        await scheduler.add_job(task1, trigger="interval", seconds=60)
        await scheduler.add_job(task2, trigger="interval", seconds=120)
        
        jobs = await scheduler.get_all_jobs()
        assert len(jobs) == 2


# ============================================================================
# Analytics Tests
# ============================================================================

class TestAnalyticsManager:
    """Test analytics framework."""
    
    @pytest.fixture
    def analytics(self):
        return AnalyticsManager()
    
    def test_add_provider(self, analytics):
        """Test adding a provider."""
        provider = NoOpProvider()
        analytics.add_provider(provider)
        
        assert "noop" in analytics.providers
        assert analytics.providers["noop"] == provider
    
    def test_remove_provider(self, analytics):
        """Test removing a provider."""
        provider = NoOpProvider()
        analytics.add_provider(provider)
        analytics.remove_provider("noop")
        
        assert "noop" not in analytics.providers
    
    async def test_track_event(self, analytics):
        """Test tracking events."""
        provider = NoOpProvider()
        analytics.add_provider(provider)
        
        await analytics.track_event("signup", {"plan": "pro"})
        # NoOp provider just logs, so test passes if no exception
        assert True
    
    async def test_track_user(self, analytics):
        """Test user tracking."""
        provider = NoOpProvider()
        analytics.add_provider(provider)
        
        await analytics.track_user("user123", {"email": "test@example.com"})
        assert True
    
    async def test_track_page(self, analytics):
        """Test page tracking."""
        provider = NoOpProvider()
        analytics.add_provider(provider)
        
        await analytics.track_page("/dashboard", {"referrer": "/login"})
        assert True
    
    async def test_identify(self, analytics):
        """Test user identification."""
        provider = NoOpProvider()
        analytics.add_provider(provider)
        
        await analytics.identify("user123", email="user@example.com", plan="pro")
        assert True
    
    async def test_multiple_providers(self, analytics):
        """Test multiple providers simultaneously."""
        ga = GoogleAnalyticsProvider(tracking_id="UA-12345678-1")
        segment = SegmentProvider(write_key="test-key")
        
        analytics.add_provider(ga)
        analytics.add_provider(segment)
        
        await analytics.track_event("purchase", {"amount": 99.99})
        
        assert len(ga.queue) > 0
        assert len(segment.queue) > 0
    
    async def test_flush(self, analytics):
        """Test flushing providers."""
        ga = GoogleAnalyticsProvider(tracking_id="UA-12345678-1")
        analytics.add_provider(ga)
        
        await analytics.track_event("event1", {})
        assert len(ga.queue) > 0
        
        await analytics.flush()
        assert len(ga.queue) == 0


# ============================================================================
# Feature Flags Tests
# ============================================================================

class TestFeatureFlags:
    """Test feature flags system."""
    
    def test_create_flag_manager(self):
        """Test creating flag manager."""
        manager = FlagManager()
        assert manager is not None
    
    async def test_set_flag_context(self):
        """Test setting flag context."""
        manager = FlagManager()
        context = FlagContext(user_id="user123", tenant="tenant1")
        
        manager.set_flag_context(context)
        current = manager.get_flag_context()
        
        assert current.user_id == "user123"
        assert current.tenant == "tenant1"
    
    async def test_flag_evaluation_always_on(self):
        """Test always-on flag."""
        manager = FlagManager()
        
        from eden.flags import Flag
        flag = Flag(
            name="new_feature",
            strategy=FlagStrategy.ALWAYS_ON,
        )
        
        manager.register_flag(flag)
        
        context = FlagContext(user_id="user123")
        manager.set_flag_context(context)
        
        result = manager.is_enabled("new_feature")
        assert result is True
    
    async def test_flag_evaluation_always_off(self):
        """Test always-off flag."""
        manager = FlagManager()
        
        from eden.flags import Flag
        flag = Flag(
            name="deprecated_feature",
            strategy=FlagStrategy.ALWAYS_OFF,
        )
        
        manager.register_flag(flag)
        
        context = FlagContext(user_id="user123")
        manager.set_flag_context(context)
        
        result = manager.is_enabled("deprecated_feature")
        assert result is False
    
    async def test_flag_evaluation_percentage_rollout(self):
        """Test percentage rollout."""
        manager = FlagManager()
        
        from eden.flags import Flag
        flag = Flag(
            name="beta_feature",
            strategy=FlagStrategy.PERCENTAGE_ROLLOUT,
            percentage=50,
        )
        
        manager.register_flag(flag)
        
        # Test consistency: same user should always get same result
        enabled_results = []
        for _ in range(5):
            context = FlagContext(user_id="user123")
            manager.set_flag_context(context)
            result = manager.is_enabled("beta_feature")
            enabled_results.append(result)
        
        # All results should be the same for same user
        assert all(r == enabled_results[0] for r in enabled_results)


# ============================================================================
# Cursor Pagination Tests
# ============================================================================

class TestCursorPagination:
    """Test cursor-based pagination."""
    
    def test_cursor_pagination_basic(self):
        """Test basic cursor pagination."""
        items = [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"},
            {"id": 3, "name": "Item 3"},
        ]
        
        paginator = CursorPaginator(sort_field="id")
        page = paginator.paginate(items, limit=2)
        
        assert len(page.items) == 2
        assert page.items[0]["id"] == 1
        assert page.has_next is True
        assert page.next_cursor is not None
    
    def test_cursor_pagination_second_page(self):
        """Test pagination to second page."""
        items = [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"},
            {"id": 3, "name": "Item 3"},
        ]
        
        paginator = CursorPaginator(sort_field="id")
        
        # First page
        page1 = paginator.paginate(items, limit=2)
        assert len(page1.items) == 2
        
        # Second page
        page2 = paginator.paginate(items, after=page1.next_cursor, limit=2)
        assert len(page2.items) == 1
        assert page2.items[0]["id"] == 3
        assert page2.has_next is False
    
    def test_cursor_pagination_bidirectional(self):
        """Test bidirectional navigation."""
        items = [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"},
            {"id": 3, "name": "Item 3"},
        ]
        
        paginator = CursorPaginator(sort_field="id")
        
        page1 = paginator.paginate(items, limit=2)
        assert page1.has_prev is False
        
        page2 = paginator.paginate(items, after=page1.next_cursor, limit=2)
        assert page2.has_prev is True
        assert page2.prev_cursor is not None


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """End-to-end integration tests."""
    
    async def test_feature_flags_with_analytics(self):
        """Test using feature flags to control analytics features."""
        manager = FlagManager()
        analytics = AnalyticsManager()
        
        from eden.flags import Flag
        flag = Flag(
            name="analytics_enabled",
            strategy=FlagStrategy.ALWAYS_ON,
        )
        manager.register_flag(flag)
        
        context = FlagContext(user_id="user123")
        manager.set_flag_context(context)
        
        if manager.is_enabled("analytics_enabled"):
            provider = GoogleAnalyticsProvider(tracking_id="UA-12345678-1")
            analytics.add_provider(provider)
        
        assert "google_analytics" in analytics.providers
    
    async def test_pagination_with_analytics_tracking(self):
        """Test tracking pagination events."""
        analytics = AnalyticsManager()
        analytics.add_provider(NoOpProvider())
        
        # Simulate pagination
        items = [{"id": i, "name": f"Item {i}"} for i in range(1, 11)]
        
        paginator = CursorPaginator(sort_field="id")
        page = paginator.paginate(items, limit=5)
        
        # Track the page view
        await analytics.track_event("pagination", {
            "page_size": 5,
            "has_next": page.has_next,
            "total_items": len(items),
        })
        
        assert len(page.items) == 5
    
    async def test_scheduler_with_analytics_flushing(self):
        """Test scheduler flushing analytics data."""
        config = SchedulerConfig(max_workers=1)
        scheduler = APSchedulerBackend(config=config)
        
        analytics = AnalyticsManager()
        analytics.add_provider(GoogleAnalyticsProvider(tracking_id="UA-12345678-1"))
        
        flush_count = [0]
        
        async def flush_analytics():
            flush_count[0] += 1
            await analytics.flush()
        
        await scheduler.start()
        
        job = await scheduler.add_job(
            flush_analytics,
            trigger="interval",
            interval_seconds=1
        )
        
        await asyncio.sleep(1.5)
        await scheduler.stop()
        
        assert flush_count[0] > 0


# ============================================================================
# Performance Tests
# ============================================================================

class TestPerformance:
    """Performance tests for new features."""
    
    def test_cursor_pagination_large_dataset(self):
        """Test cursor pagination performance with large dataset."""
        # Create 10,000 items
        items = [{"id": i, "name": f"Item {i}", "value": i * 2} for i in range(1, 10001)]
        
        paginator = CursorPaginator(sort_field="id")
        
        # Paginate through
        page = paginator.paginate(items, limit=100)
        assert len(page.items) == 100
        
        # Jump to middle (100 pages in)
        current = page
        for _ in range(99):
            if current.has_next:
                current = paginator.paginate(items, after=current.next_cursor, limit=100)
        
        # Should be at items ~10000
        assert current.items[-1]["id"] > 9900
    
    async def test_analytics_batch_processing(self):
        """Test analytics batch flushing."""
        analytics = AnalyticsManager()
        provider = GoogleAnalyticsProvider(tracking_id="UA-12345678-1")
        provider.batch_size = 10
        analytics.add_provider(provider)
        
        # Track 25 events
        for i in range(25):
            await analytics.track_event(f"event_{i}", {"index": i})
        
        # Should have flushed once (at 10 items, queue now has 15)
        assert len(provider.queue) >= 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
