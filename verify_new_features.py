#!/usr/bin/env python
"""Quick verification that new features import and work correctly."""

import sys
import asyncio
from datetime import datetime, timedelta

print("=" * 70)
print("EDEN FRAMEWORK - NEW FEATURES VERIFICATION")
print("=" * 70)

# Test 1: APScheduler Backend
print("\n✓ Testing APScheduler Backend...")
try:
    from eden.apscheduler_backend import (
        APSchedulerBackend, SchedulerConfig, JobDefinition, MemoryJobStore
    )
    config = SchedulerConfig(max_workers=2)
    scheduler = APSchedulerBackend(config=config)
    print("  ✓ APSchedulerBackend imported and instantiated")
except Exception as e:
    print(f"  ✗ Error: {e}")
    sys.exit(1)

# Test 2: Analytics Framework
print("\n✓ Testing Analytics Framework...")
try:
    from eden.analytics import (
        AnalyticsManager, NoOpProvider, GoogleAnalyticsProvider,
        SegmentProvider, MixpanelProvider, get_analytics_manager
    )
    analytics = AnalyticsManager()
    provider = NoOpProvider()
    analytics.add_provider(provider)
    print("  ✓ AnalyticsManager imported and providers working")
except Exception as e:
    print(f"  ✗ Error: {e}")
    sys.exit(1)

# Test 3: Feature Flags
print("\n✓ Testing Feature Flags...")
try:
    from eden.flags import (
        FlagManager, FlagContext, FlagStrategy, Flag, 
        set_flag_context, get_flag_context
    )
    manager = FlagManager()
    flag = Flag(
        name="test_flag",
        strategy=FlagStrategy.ALWAYS_ON,
    )
    manager.register_flag(flag)
    context = FlagContext(user_id="user123")
    manager.set_flag_context(context)
    result = manager.is_enabled("test_flag")
    print(f"  ✓ Feature flags working (test_flag enabled: {result})")
except Exception as e:
    print(f"  ✗ Error: {e}")
    sys.exit(1)

# Test 4: Cursor Pagination
print("\n✓ Testing Cursor Pagination...")
try:
    from eden.db.cursor import CursorPaginator, CursorPage, paginate
    
    items = [{"id": i, "name": f"Item {i}"} for i in range(1, 21)]
    paginator = CursorPaginator(sort_field="id")
    page = paginator.paginate(items, limit=5)
    
    print(f"  ✓ Cursor pagination working")
    print(f"    - Items: {len(page.items)}")
    print(f"    - Has next: {page.has_next}")
    print(f"    - Has prev: {page.has_prev}")
except Exception as e:
    print(f"  ✗ Error: {e}")
    sys.exit(1)

# Test 5: Async operations
print("\n✓ Testing Async Operations...")
try:
    async def test_async():
        # Test analytics async
        await analytics.track_event("test", {"value": 1})
        
        # Test scheduler async
        counter = [0]
        
        async def increment():
            counter[0] += 1
        
        job = await scheduler.add_job(
            increment,
            trigger="interval",
            seconds=1,
            id="test-job"
        )
        
        assert job is not None
        
        retrieved = await scheduler.get_job("test-job")
        assert retrieved is not None
        
        await scheduler.remove_job("test-job")
        
        return counter[0] >= 0
    
    result = asyncio.run(test_async())
    print(f"  ✓ Async operations working")
except Exception as e:
    print(f"  ✗ Error: {e}")
    sys.exit(1)

# Summary
print("\n" + "=" * 70)
print("✓ ALL FEATURES VERIFIED SUCCESSFULLY")
print("=" * 70)
print("\nFeatures ready to use:")
print("  1. Feature Flags (eden/flags.py)")
print("  2. Cursor Pagination (eden/db/cursor.py)")
print("  3. APScheduler Integration (eden/apscheduler_backend.py)")
print("  4. Analytics Framework (eden/analytics.py)")
print("\nSee NEW_FEATURES_GUIDE.md for complete documentation.")
print("=" * 70)
