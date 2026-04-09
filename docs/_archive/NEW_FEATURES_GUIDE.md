# New Features Implementation Guide

Complete reference for Feature Flags, Cursor Pagination, APScheduler, and Analytics in Eden Framework.

---

## Table of Contents

1. [Feature Flags](#feature-flags)
2. [Cursor Pagination](#cursor-pagination)
3. [APScheduler Integration](#apscheduler-integration)
4. [Analytics Framework](#analytics-framework)
5. [Integration Examples](#integration-examples)

---

## Feature Flags

**Location:** `eden/flags.py`

### Overview

Dynamic feature flags system with multiple evaluation strategies and backends. Supports:

- 7 evaluation strategies (always-on/off, percentage rollout, user/segment/tenant/environment-based)
- Thread-safe context variables for request-scoped access
- Deterministic percentage rollout for consistent user experiences
- Multiple backends (in-memory, database stub)

### Quick Start

```python
from eden.flags import FlagManager, FlagContext, FlagStrategy, Flag

# Create manager
manager = FlagManager()

# Define a feature flag
flag = Flag(
    name="new_dashboard",
    strategy=FlagStrategy.PERCENTAGE_ROLLOUT,
    percentage=50,
    description="New dashboard UI for 50% of users"
)

manager.register_flag(flag)

# Set request context
context = FlagContext(
    user_id="user123",
    tenant="tenant_id",
    environment="production"
)
manager.set_flag_context(context)

# Check if enabled
if manager.is_enabled("new_dashboard"):
    # Use new feature
    pass
```

### Strategies

| Strategy | Use Case | Parameters |
|----------|----------|------------|
| `ALWAYS_ON` | Global rollout | None |
| `ALWAYS_OFF` | Feature disabled/deprecated | None |
| `PERCENTAGE_ROLLOUT` | Gradual rollout | `percentage` (0-100) |
| `USER_WHITELIST` | Specific users | `user_ids: List[str]` |
| `SEGMENT_BASED` | User segments | `segments: List[str]` |
| `TENANT_BASED` | Multi-tenant control | `tenant_ids: List[str]` |
| `ENVIRONMENT_BASED` | Environment-specific | `environments: List[str]` |

### Percentage Rollout Details

Uses MD5 hashing of user_id for deterministic, consistent rollout:

```python
# User "user123" gets same result every request
hash_value = md5(f"new_feature:user123".encode()).hexdigest()
user_hash_int = int(hash_value[:8], 16)
enabled = (user_hash_int % 100) < 50  # 50% rollout
```

This ensures:
- ✅ Same user always gets same result
- ✅ Even distribution across percentage ranges
- ✅ No database lookups for consistency check

### Application Integration

```python
from fastapi import FastAPI, Request
from eden.flags import set_flag_context, FlagContext

app = FastAPI()

@app.middleware("http")
async def add_flag_context(request: Request, call_next):
    user_id = request.headers.get("X-User-ID", "anonymous")
    tenant = request.headers.get("X-Tenant-ID", "default")
    
    context = FlagContext(
        user_id=user_id,
        tenant=tenant,
        environment="production"
    )
    set_flag_context(context)
    
    response = await call_next(request)
    return response
```

---

## Cursor Pagination

**Location:** `eden/db/cursor.py`

### Overview

Keyset-based (cursor) pagination for efficient navigation of large datasets. Key benefits:

- **O(1) performance** - No OFFSET scanning
- **Stable** - Consistent results even with concurrent inserts
- **Bidirectional** - Navigate forward and backward
- **Stateless** - Cursor contains all needed data

### Quick Start

```python
from eden.db.cursor import CursorPaginator, paginate

# Create paginator (sort by id, ascending)
paginator = CursorPaginator(sort_field="id", reverse=False)

# Get first page
page = paginator.paginate(items, limit=20)

print(f"Got {len(page.items)} items")
print(f"Has next: {page.has_next}")
print(f"Has prev: {page.has_prev}")

# Next page
if page.has_next:
    next_page = paginator.paginate(
        items,
        after=page.next_cursor,
        limit=20
    )

# Previous page
if page.has_prev:
    prev_page = paginator.paginate(
        items,
        before=page.prev_cursor,
        limit=20
    )
```

### Cursor Format

Cursors are base64-encoded JSON containing sort field values:

```
eyJpZCI6IDUwfQ==  →  {"id": 50}
```

### With SQL Queries

```python
from eden.db.cursor import paginate
from sqlalchemy import select
from myapp.models import User

# Get first page
page = await paginate(
    select(User),
    session=db_session,
    limit=20,
    sort_field="id",
)

# Pagination in API
return {
    "items": [u.dict() for u in page.items],
    "cursor": page.next_cursor,
    "has_next": page.has_next,
}
```

### Advanced Usage

```python
# Multiple sort fields
class MultiSort:
    def __init__(self, primary, secondary=None):
        self.primary = primary
        self.secondary = secondary

# Sort by created_at (descending), then by id
paginator = CursorPaginator(sort_field="created_at", reverse=True)

# Sort by different field
paginator = CursorPaginator(sort_field="name")
page = paginator.paginate(users, limit=50)
```

### Performance Comparison

For 1M rows:

| Method | Time | Notes |
|--------|------|-------|
| OFFSET 100,000 | ~5s | Scans first 100k rows |
| Cursor 100,000 | ~50ms | Direct seek |
| OFFSET 500,000 | ~25s | Scans first 500k rows |
| Cursor 500,000 | ~50ms | Direct seek |

---

## APScheduler Integration

**Location:** `eden/apscheduler_backend.py`

### Overview

Enterprise-grade scheduled task execution with:

- Persistent job storage
- Multiple executor types
- Job triggers: cron, interval, date
- Job retry and error handling
- Concurrent execution limits

### Quick Start

```python
from eden.apscheduler_backend import APSchedulerBackend, SchedulerConfig
from fastapi import FastAPI

app = FastAPI()
scheduler = None

@app.on_event("startup")
async def start_scheduler():
    global scheduler
    config = SchedulerConfig(
        job_store="memory",
        max_workers=4,
        timezone="UTC"
    )
    scheduler = APSchedulerBackend(config=config)
    await scheduler.start()

@app.on_event("shutdown")
async def stop_scheduler():
    global scheduler
    await scheduler.stop()
```

### Scheduling Jobs

**Interval Job (repeating):**

```python
async def send_digest():
    print("Sending digest email...")

await scheduler.add_job(
    send_digest,
    trigger="interval",
    seconds=3600,  # Every hour
)
```

**Cron Job (scheduled time):**

```python
await scheduler.add_job(
    send_digest,
    trigger="cron",
    hour=9,
    minute=0,
    day_of_week="mon-fri",
)
```

**Date Job (one-time):**

```python
from datetime import datetime, timedelta

await scheduler.add_job(
    send_email,
    trigger="date",
    run_date=datetime.now() + timedelta(hours=2),
    kwargs={"recipient": "user@example.com"}
)
```

### Job Management

```python
# Add job with custom ID
job = await scheduler.add_job(
    my_task,
    trigger="interval",
    seconds=3600,
    id="task-send-digest",
    name="Send Digest",
    description="Send daily digest email"
)

# Get job
job = await scheduler.get_job("task-send-digest")

# Remove job
await scheduler.remove_job("task-send-digest")

# List all jobs
jobs = await scheduler.get_all_jobs()
for job in jobs:
    print(f"{job.id}: {job.name}")
```

### Job Function Options

```python
# Async function
async def async_task(user_id, action="notify"):
    print(f"Processing {action} for user {user_id}")

# Sync function
def sync_task(user_id):
    print(f"Processing user {user_id}")

# With arguments
await scheduler.add_job(
    async_task,
    trigger="interval",
    seconds=300,
    kwargs={"user_id": "user123", "action": "remind"}
)
```

### Configuration

```python
config = SchedulerConfig(
    job_store="memory",           # memory or database
    max_workers=4,                # Concurrent job executors
    timezone="UTC",               # Job timezone
    misfire_grace_time=60,        # Grace period for missed jobs
    job_defaults_coalesce=True,   # Combine missed runs
    job_defaults_max_instances=1, # Max concurrent instances
)

scheduler = APSchedulerBackend(config=config)
```

### Error Handling

```python
async def robust_task():
    try:
        # Do something
        pass
    except Exception as e:
        logger.error(f"Task failed: {e}")
        # APScheduler will retry based on config

await scheduler.add_job(
    robust_task,
    trigger="interval",
    seconds=3600,
)
```

---

## Analytics Framework

**Location:** `eden/analytics.py`

### Overview

Plugin architecture for multiple analytics providers:

- Multiple providers simultaneously
- Automatic event tracking
- Batch processing
- Built-in providers: Google Analytics, Segment, Mixpanel

### Quick Start

```python
from eden.analytics import AnalyticsManager, GoogleAnalyticsProvider
from fastapi import FastAPI

app = FastAPI()
analytics = AnalyticsManager()

@app.on_event("startup")
async def setup_analytics():
    # Add Google Analytics
    ga = GoogleAnalyticsProvider(tracking_id="UA-12345678-1")
    analytics.add_provider(ga)
    
    # Add Segment
    from eden.analytics import SegmentProvider
    segment = SegmentProvider(write_key="write_key_123")
    analytics.add_provider(segment)
    
    # Start auto-flush every 60 seconds
    await analytics.start_auto_flush(interval=60)
```

### Event Tracking

```python
# Track custom event
await analytics.track_event("user_signup", {
    "plan": "pro",
    "referral_code": "REF123"
})

# Track user information
await analytics.track_user("user123", {
    "email": "user@example.com",
    "plan": "premium",
    "signup_date": "2024-01-15"
})

# Track page view
await analytics.track_page("/dashboard", {
    "referrer": "/login",
    "theme": "dark"
})

# Identify user
await analytics.identify(
    "user123",
    email="user@example.com",
    plan="pro",
    lifetime_value=9999
)
```

### Supported Providers

#### Google Analytics

```python
ga = GoogleAnalyticsProvider(tracking_id="UA-12345678-1")
analytics.add_provider(ga)

# Tracks events in Google Analytics format
await analytics.track_event("purchase", {"amount": 99.99})
```

#### Segment

```python
segment = SegmentProvider(write_key="YOUR_WRITE_KEY")
analytics.add_provider(segment)

# Tracks via Segment platform
await analytics.track_event("payment_processed", {"status": "success"})
```

#### Mixpanel

```python
mixpanel = MixpanelProvider(token="YOUR_TOKEN")
analytics.add_provider(mixpanel)

# Tracks in Mixpanel
await analytics.track_event("feature_used", {"feature": "export"})
```

#### Custom Provider

```python
from eden.analytics import AnalyticsProvider

class CustomProvider(AnalyticsProvider):
    name = "custom"
    
    async def track_event(self, event_name, properties=None):
        # Custom implementation
        await self._queue_event({
            "event": event_name,
            "props": properties
        })
    
    async def flush(self):
        # Send to custom backend
        for event in self.queue:
            await send_to_backend(event)
        self.queue.clear()

analytics.add_provider(CustomProvider())
```

### Middleware Integration

```python
from fastapi import Request
from contextlib import asynccontextmanager

analytics = AnalyticsManager()

@app.middleware("http")
async def track_analytics(request: Request, call_next):
    response = await call_next(request)
    
    # Track page view
    await analytics.track_page(
        request.url.path,
        {
            "method": request.method,
            "status": response.status_code,
        }
    )
    
    return response
```

### Batch Processing

```python
# Automatic batching (when queue reaches batch_size)
ga = GoogleAnalyticsProvider(tracking_id="UA-12345678-1")
ga.batch_size = 100  # Flush after 100 events

analytics.add_provider(ga)

# Track events
for i in range(250):
    await analytics.track_event(f"event_{i}", {"index": i})
    # Auto-flushes at 100 and 200 events

# Final flush
await analytics.flush()
```

---

## Integration Examples

### 1. Feature Flags + Analytics

Control analytics collection with feature flags:

```python
manager = FlagManager()
analytics = AnalyticsManager()

# Only track with GA if flag enabled
context = FlagContext(user_id="user123")
manager.set_flag_context(context)

if manager.is_enabled("analytics_enabled"):
    provider = GoogleAnalyticsProvider(tracking_id="UA-123")
    analytics.add_provider(provider)

# Track normally
await analytics.track_event("user_action", {})
```

### 2. Cursor Pagination + Analytics

Track pagination events:

```python
paginator = CursorPaginator(sort_field="id")
analytics = AnalyticsManager()

page = paginator.paginate(items, limit=50)

await analytics.track_event("pagination", {
    "page_size": 50,
    "has_next": page.has_next,
    "cursor_position": page.next_cursor[:10] if page.next_cursor else None,
})
```

### 3. APScheduler + Analytics

Periodic analytics flushing:

```python
scheduler = APSchedulerBackend()
analytics = AnalyticsManager()

await scheduler.add_job(
    analytics.flush,
    trigger="interval",
    seconds=60,
    id="job-flush-analytics"
)

await scheduler.start()
```

### 4. Complete App Setup

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request

app = FastAPI()

# Scheduler
scheduler = None

# Analytics
analytics = AnalyticsManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global scheduler
    
    config = SchedulerConfig(max_workers=4)
    scheduler = APSchedulerBackend(config=config)
    await scheduler.start()
    
    provider = GoogleAnalyticsProvider(tracking_id="UA-12345678-1")
    analytics.add_provider(provider)
    
    # Set up periodic flush
    await scheduler.add_job(
        analytics.flush,
        trigger="interval",
        seconds=60,
        id="flush-analytics"
    )
    
    yield
    
    # Shutdown
    await analytics.flush()
    await scheduler.stop()

app = FastAPI(lifespan=lifespan)

@app.middleware("http")
async def track_requests(request: Request, call_next):
    await analytics.track_page(
        request.url.path,
        {"method": request.method}
    )
    response = await call_next(request)
    return response

@app.get("/api/items")
async def list_items(page: str = None):
    items = get_all_items()
    
    paginator = CursorPaginator(sort_field="id")
    result = paginator.paginate(
        items,
        after=page,
        limit=50
    )
    
    await analytics.track_event("items_listed", {
        "count": len(result.items),
        "has_next": result.has_next,
    })
    
    return {
        "items": result.items,
        "next": result.next_cursor,
    }
```

---

## Testing

Run integration tests:

```bash
pytest tests/test_new_features_integration.py -v

# Specific test
pytest tests/test_new_features_integration.py::TestFeatureFlags -v

# Performance tests
pytest tests/test_new_features_integration.py::TestPerformance -v
```

---

## Migration Guide

### From Croniter to APScheduler

**Before (croniter):**

```python
from croniter import croniter
from datetime import datetime

cron = croniter('0 9 * * *', datetime.now())
next_time = cron.get_next(datetime)
```

**After (APScheduler):**

```python
scheduler = APSchedulerBackend()

async def send_digest():
    pass

await scheduler.add_job(
    send_digest,
    trigger="cron",
    hour=9,
    minute=0,
)
```

---

## Troubleshooting

### Feature Flags not working

```python
# Make sure context is set
manager.set_flag_context(FlagContext(user_id="user123"))

# Check if flag is registered
flags = manager.get_all_flags()
assert "feature_name" in flags
```

### Analytics not flushing

```python
# Manually flush
await analytics.flush()

# Check queue size
for provider in analytics.providers.values():
    print(f"{provider.name} queue: {len(provider.queue)}")
```

### Scheduler not executing jobs

```python
# Verify scheduler is running
assert scheduler.running is True

# Check job list
jobs = await scheduler.get_all_jobs()
for job in jobs:
    print(f"{job.id}: next_run={job.next_run_time}")
```

---

## Performance Tuning

### Analytics Batch Size

Larger batches = fewer API calls:

```python
provider.batch_size = 200  # Default 100
```

### Scheduler Workers

More workers = more concurrent jobs:

```python
config = SchedulerConfig(max_workers=8)  # Default 4
```

### Pagination Limit

Find optimal limit for your data:

```python
# Recommended: 20-100 items
page = paginator.paginate(items, limit=50)
```

---

## References

- [Feature Flags Implementation](eden/flags.py)
- [Cursor Pagination Implementation](eden/db/cursor.py)
- [APScheduler Integration](eden/apscheduler_backend.py)
- [Analytics Framework](eden/analytics.py)
- [Integration Tests](tests/test_new_features_integration.py)
