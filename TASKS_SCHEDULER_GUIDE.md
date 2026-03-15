# Eden Task Queue & Scheduler Guide

Complete reference for background task execution, periodic scheduling, and error recovery in Eden Framework.

## Overview

The Eden task system provides production-ready background job execution with:

- **One-shot tasks**: Fire-and-forget background jobs with retry support
- **Periodic tasks**: Repeating jobs (interval-based or cron expressions)
- **Error recovery**: Exponential backoff (1s, 2s, 4s, 8s, 16s) with configurable retries
- **Result storage**: Track task execution outcomes and failures
- **Dead-letter queue**: Monitor permanently failed tasks
- **Lifecycle integration**: Automatic startup/shutdown with app

Built on **Taskiq** (in-memory or Redis) with **APScheduler** for production-grade cron support.

---

## Quick Start

### Basic Background Task

```python
from eden import Eden

app = Eden(__name__)

# Define a background task
@app.task()
async def send_email(to: str, subject: str):
    """Send an email in the background."""
    print(f"Sending email to {to}: {subject}")
    # Your email logic here

# Trigger it asynchronously
@app.post("/newsletter")
async def subscribe(ctx):
    await ctx.app.task.defer(send_email, to="user@example.com", subject="Welcome!")
    return {"status": "subscribed"}
```

### Periodic Task (Every N Seconds/Minutes/Hours)

```python
@app.task.every(minutes=5)
async def refresh_cache():
    """Run every 5 minutes during app uptime."""
    print("Refreshing cache...")
    # Cache update logic

# Or with specific interval
@app.task.every(hours=1, minutes=30)
async def backup_database():
    """Run every 1.5 hours."""
    pass
```

### Delayed Execution

```python
# Send an email 1 hour from now
await app.task.schedule(send_email, delay=3600, to="user@example.com", subject="Reminder")
```

---

## Core Concepts

### EdenBroker

The main broker class managing all task operations:

```python
# Access broker from any route/handler
broker = app.broker

# Properties
broker.periodic_tasks      # List of PeriodicTask objects
broker.result_backend      # Task result storage (TaskResultBackend)
broker.is_running          # Whether broker is active
broker.max_retries         # Max retry attempts (default: 5)
broker.retry_delays        # Backoff delays in seconds (default: [1, 2, 4, 8, 16])
```

### TaskResult

Represents the outcome of a task execution:

```python
@dataclass
class TaskResult:
    task_id: str                    # Unique task identifier
    task_name: str                  # Function name
    status: str                     # "success", "failed", "dead_letter"
    result: Any = None              # Task return value (if successful)
    error: str | None = None        # Error message (if failed)
    error_traceback: str | None = None  # Full traceback
    retries: int = 0                # Number of retries performed
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    ttl_seconds: int = 604800       # Keep for 7 days by default
```

### PeriodicTask

Controls a repeating task registration:

```python
task = app.broker.periodic_tasks[0]

task.func                  # The actual function
task.interval              # Interval in seconds (0 if cron-based)
task.cron                  # Cron expression (if cron-based)
task.execution_count       # How many times it's run
task.last_error            # Last exception, if any

# Methods (normally called by broker)
task.start()               # Start the periodic loop
task.stop()                # Stop the periodic loop
```

---

## Task Registration

### Decorator Syntax

```python
# One-shot task
@app.task()
async def background_work(param: str):
    return f"Done: {param}"

# Periodic task
@app.task.every(minutes=10)
async def cleanup():
    pass

# Periodic with cron (future enhancement)
@app.task.every(cron="0 12 * * *")
async def daily_report():
    pass
```

### Both Sync and Async Functions Supported

```python
# Async task (preferred)
@app.task()
async def async_email():
    await send_to_provider()

# Sync task (also works)
@app.task()
def sync_email():
    send_to_provider_blocking()
    
# Periodic tasks handle both
@app.task.every(seconds=30)
def sync_periodic():
    print("Runs every 30 seconds")
```

---

## Executing Tasks

### Fire-and-Forget (Immediate)

```python
# Raise error if broker isn't running (safe check)
try:
    await app.task.defer(send_email, to="user@example.com", subject="Hi")
except BrokerNotInitialized:
    logger.error("Broker not started!")

# Passes task ID back if available
result = await app.task.defer(send_email, to="user@example.com")
```

### Delayed Execution

```python
# Execute after N seconds
await app.task.schedule(send_email, delay=3600, to="user@example.com", subject="Later")

# Also requires broker startup
```

### In HTTP Routes

```python
@app.post("/users")
async def create_user(ctx):
    user = await User.create(name=ctx.body["name"])
    
    # Send welcome email in background
    await ctx.app.task.defer(send_welcome_email, user_id=user.id)
    
    return {"status": "created", "user_id": user.id}
```

---

## Error Recovery & Retries

### Exponential Backoff

By default, failed tasks retry with increasing delays:

```
Attempt 1: Fails immediately
Attempt 2: Waits 1 second, retries
Attempt 3: Waits 2 seconds, retries
Attempt 4: Waits 4 seconds, retries
Attempt 5: Waits 8 seconds, retries
Attempt 6: Waits 16 seconds, retries
Attempt 7: Fails permanently → Dead-Letter Queue
```

### Configuration

```python
# Custom retry settings
from eden.tasks import create_broker

broker = create_broker(redis_url=None)
app.broker = EdenBroker(
    broker,
    max_retries=3,
    retry_delays=[1, 3, 10]  # 1s, 3s, 10s
)

# Now tasks retry max 3 times with custom delays
```

### Task Result Tracking

```python
# Get task result by ID
result = await app.broker.result_backend.get_result(task_id)
if result:
    print(f"Status: {result.status}")
    print(f"Result: {result.result}")
    print(f"Error: {result.error}")
    print(f"Retries: {result.retries}")
```

---

## Dead-Letter Queue

Tasks that permanently fail (exhaust retries) go to the dead-letter queue:

```python
# Get all dead-letter tasks
dead_letters = await app.broker.get_dead_letter_tasks()

for task in dead_letters:
    print(f"Task: {task.task_name}")
    print(f"Error: {task.error}")
    print(f"Traceback: {task.error_traceback}")
    print(f"Retries exhausted: {task.retries}")

# Clear dead-letter queue
cleared = await app.broker.result_backend.clear_dead_letter()
print(f"Cleared {cleared} dead tasks")
```

---

## Periodic Tasks Management

### View Registered Periodic Tasks

```python
for task in app.broker.periodic_tasks:
    print(f"Task: {task.func.__name__}")
    print(f"Interval: {task.interval}s")
    print(f"Runs completed: {task.execution_count}")
    print(f"Last error: {task.last_error}")
```

### Via CLI

```bash
# List all periodic tasks
eden tasks list

# View broker status and task counts
eden tasks status

# View dead-letter tasks
eden tasks dead-letter
```

---

## CLI Commands

### Start Worker Process

```bash
# Start 4 worker processes
eden tasks worker --workers 4

# Or 1 worker (default)
eden tasks worker
```

### Run Periodic Task Scheduler

```bash
# Start scheduler (runs periodic tasks on schedule)
eden tasks scheduler

# Keep running in background during app uptime
```

### List Registered Tasks

```bash
# Show all @app.task() and @app.task.every() registrations
eden tasks list
```

### View Statistics

```bash
# Show broker info and task counts
eden tasks status

# Output:
# Broker Status: Running
# Broker Type: InMemoryBroker
# Periodic Tasks: 5
# Task Results Stored: 42
# Dead-Letter Queue: 3
```

### View Dead-Letter Queue

```bash
# Show tasks that failed permanently
eden tasks dead-letter

# Output:
# Dead-Letter Queue (3 tasks):
# 1. send_email (failed after 6 retries)
#    Last error: Connection timeout
# 2. backup_database (failed after 5 retries)
#    Last error: Disk full
```

---

## App Lifecycle Integration

### Automatic Startup/Shutdown

The broker starts/stops automatically with your app:

```python
# Broker starts when app starts
# - All @app.task() registrations become available
# - All @app.task.every() tasks begin executing on schedule

# Broker stops when app stops
# - Periodic tasks are cancelled
# - Task results are cleaned up (expired ones removed)
# - Redis connection (if used) is closed
```

### Manual Control (Advanced)

```python
# If you need manual control:
await app.broker.startup()      # Start broker
await app.broker.shutdown()     # Stop broker

# Or use setup_tasks() helper
app.setup_tasks()  # Initializes result backend, etc.
```

---

## Advanced: Custom Broker Configuration

### Redis Backing

For production with multiple processes:

```python
from eden.tasks import EdenBroker, create_broker

# Use Redis instead of in-memory
redis_broker = create_broker(redis_url="redis://localhost:6379")
app.broker = EdenBroker(redis_broker)

# Now tasks persist across process restarts
```

### Custom Retry Configuration

```python
from eden.tasks import EdenBroker, create_broker

broker = create_broker()
app.broker = EdenBroker(
    broker,
    max_retries=10,
    retry_delays=[0.5, 1, 2, 4, 8, 16, 32, 64, 128, 256]  # 10 retries
)
```

### Task Result TTL

By default, results keep for 7 days:

```python
result = TaskResult(
    task_id="...",
    task_name="send_email",
    status="success",
    ttl_seconds=86400  # Keep for 1 day instead
)

await app.broker.result_backend.store_result(result.task_id, result)
```

### Cleanup Old Results

```python
# Remove expired results manually
expired_count = await app.broker.result_backend.cleanup_expired()
print(f"Cleaned up {expired_count} expired results")

# Also called automatically on app shutdown
```

---

## Exception Reference

### TaskError

Base exception for all task issues.

### BrokerNotInitialized

Raised when calling `defer()` or `schedule()` before broker startup:

```python
try:
    await app.task.defer(my_task)
except BrokerNotInitialized as e:
    logger.error(f"Broker not ready: {e}")
```

### TaskExecutionError

Raised when a task fails during execution:

```python
try:
    result = await run_task()
except TaskExecutionError as e:
    print(f"Task {e.task_id} failed")
    print(f"Retries so far: {e.retry_count}")
    print(f"Original error: {e.original_exception}")
```

### MaxRetriesExceeded

Raised when task exhausts all retries:

```python
except MaxRetriesExceeded as e:
    print(f"Task {e.task_id} failed permanently")
    print(f"Max retries: {e.max_retries}")
    print(f"Final error: {e.last_error}")
```

### SchedulerError

Base exception for scheduler operations.

### InvalidCronExpression

Raised when cron expression is invalid:

```python
from eden.tasks.exceptions import InvalidCronExpression

try:
    @app.task.every(cron="invalid")
except InvalidCronExpression as e:
    print(f"Bad cron: {e.expression}")
    print(f"Reason: {e.reason}")
```

### JobNotFound

Raised when scheduler can't find a job to manage:

```python
from eden.tasks.apscheduler_backend import APSchedulerBackend

scheduler = APSchedulerBackend()
try:
    scheduler.pause_job("missing_job_id")
except JobNotFound as e:
    print(f"Job not found: {e.job_id}")
```

---

## Common Patterns

### Email Notifications

```python
@app.task()
async def send_email(to: str, subject: str, body: str):
    """Send email with retry on failure."""
    async with aiosmtplib.SMTP() as smtp:
        await smtp.send_message(
            email.message_from_string(...)
        )

# Trigger from route
@app.post("/notify")
async def notify_user(ctx):
    await ctx.app.task.defer(
        send_email,
        to=ctx.body["email"],
        subject="Notification",
        body="You have a message"
    )
    return {"status": "sent"}
```

### Cleanup Tasks

```python
@app.task.every(hours=1)
async def cleanup_old_tempfiles():
    """Remove temp files older than 1 day."""
    import os
    from pathlib import Path
    
    temp_dir = Path("/tmp/eden")
    cutoff = datetime.now() - timedelta(days=1)
    
    for file in temp_dir.glob("*"):
        if datetime.fromtimestamp(file.stat().st_mtime) < cutoff:
            file.unlink()

# Runs every hour automatically
```

### Report Generation

```python
@app.task.every(minutes=30)
async def update_analytics():
    """Refresh analytics cache every 30 minutes."""
    data = await gather_metrics()
    await cache.set("analytics", data, ex=1800)
    logger.info("Analytics refreshed")

@app.get("/dashboard")
async def dashboard(ctx):
    # Always get fresh cached data
    analytics = await cache.get("analytics")
    return {"data": analytics}
```

### Scheduled Maintenance

```python
@app.task.every(hours=2)
async def archive_old_logs():
    """Move old log files to cold storage."""
    logs = await LogEntry.where(
        created_at__lt=datetime.now() - timedelta(days=30)
    )
    for log in logs:
        await s3.upload(log)
        await log.delete()
    logger.info(f"Archived {len(logs)} old logs")
```

---

## Performance Considerations

### Task Size

Keep tasks small and focused:

```python
# ✅ Good: specific task
@app.task()
async def send_welcome_email(user_id: int):
    user = await User.get(user_id)
    await email_provider.send(user.email, "Welcome!")

# ❌ Bad: doing too much
@app.task()
async def process_everything(user_id: int):
    user = await User.get(user_id)
    await send_emails()
    await generate_reports()
    await update_cache()
    # ... 50 other things
```

### Timeout Handling

Set reasonable timeout expectations:

```python
# For Taskiq/async operations
# Default broker timeout should be set based on task type

# For periodic tasks
@app.task.every(minutes=5)
async def quick_task():
    # Should complete in < 5 minutes
    # Otherwise will overlap with next run
    await do_something()
```

### Result Storage

Clean up old results periodically:

```python
@app.task.every(days=1)
async def cleanup_old_results():
    """Remove task results older than 7 days."""
    cleaned = await app.broker.result_backend.cleanup_expired()
    logger.info(f"Cleaned {cleaned} old results")
```

### Redis vs In-Memory

- **In-memory**: Fast, no network, single process only
- **Redis**: Multi-process, persistent, network overhead

```python
# Use in-memory for development
dev_broker = create_broker()

# Use Redis for production
prod_broker = create_broker(redis_url=os.getenv("REDIS_URL"))
```

---

## Testing

### Mock Task Execution

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_user_signup_sends_email(app):
    """Test that signup triggers welcome email."""
    
    with patch.object(app.task, 'defer', new_callable=AsyncMock) as mock_defer:
        # Execute signup
        result = await simulate_signup(user_data)
        
        # Verify email task was queued
        mock_defer.assert_called_once()
        call_args = mock_defer.call_args
        assert call_args[0][0].__name__ == "send_email"
        assert call_args[1]["to"] == "user@example.com"
```

### Test Periodic Task Execution

```python
@pytest.mark.asyncio
async def test_cleanup_task_runs():
    """Test that periodic cleanup task executes."""
    from tests.test_tasks_full import TestPeriodicTasks
    
    # Uses app.broker.periodic_tasks[0].execution_count
    await app.broker.startup()
    await asyncio.sleep(0.1)  # Let task run
    
    assert app.broker.periodic_tasks[0].execution_count > 0
    
    await app.broker.shutdown()
```

### Full Integration Test

```python
@pytest.mark.asyncio
async def test_task_with_error_recovery(app):
    """Test task failure and retry."""
    call_count = 0
    
    @app.task()
    async def flaky_task():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("Simulated failure")
        return "success"
    
    await app.broker.startup()
    await app.task.defer(flaky_task)
    
    # Give retries time to execute
    await asyncio.sleep(10)
    
    # Should have retried
    assert call_count >= 3
    
    await app.broker.shutdown()
```

---

## Troubleshooting

### "BrokerNotInitialized" Error

The broker isn't running when you try to defer/schedule a task.

**Solution:** Ensure `app.setup_tasks()` or `app.broker.startup()` is called:

```python
# Automatic (normal case)
async with app:
    # Broker runs here
    pass

# Manual (rare)
await app.broker.startup()
await app.task.defer(my_task)
await app.broker.shutdown()
```

### Periodic Task Not Running

Task is registered but not executing.

**Solution:** Check if interval is > 0:

```python
# ✅ Works
@app.task.every(seconds=30)

# ❌ Fails silently (0 interval)
@app.task.every()
```

### Tasks Pile Up in Dead-Letter

Many failed tasks accumulating.

**Debug steps:**

```python
# 1. Check dead-letter queue
dead = await app.broker.get_dead_letter_tasks()
print(f"Failed tasks: {len(dead)}")

# 2. Examine error details
for task in dead[:1]:
    print(f"Error: {task.error}")
    print(f"Traceback: {task.error_traceback}")

# 3. Fix the underlying issue
# 4. Clear dead-letter
await app.broker.result_backend.clear_dead_letter()
```

### Redis Connection Failures

```python
# Check Redis is running
redis-cli ping

# Verify connection string
REDIS_URL=redis://localhost:6379

# Test connection
python -c "from redis import Redis; Redis.from_url('redis://localhost:6379').ping()"
```

### Tasks Not Persisting (Using Redis)

Make sure Redis URL is correct:

```python
from eden.tasks import create_broker

broker = create_broker(redis_url="redis://localhost:6379/0")
# Test it
await broker.startup()
# If it fails, check Redis is running
```

---

## Architecture

```
┌─ Eden App
│  ├─ EdenBroker
│  │  ├─ TaskIQ AsyncBroker (in-memory or Redis)
│  │  ├─ TaskResultBackend (stores results + dead-letter)
│  │  └─ PeriodicTasks (list of running scheduled tasks)
│  │
│  └─ Lifecycle
│     ├─ app.on_startup → broker.startup()
│     │  ├─ Initialize TaskIQ broker
│     │  └─ Start all periodic tasks
│     │
│     └─ app.on_shutdown → broker.shutdown()
│        ├─ Stop all periodic tasks
│        ├─ Clean expired results
│        └─ Close broker connections
│
└─ TaskIQ (Background Task Queue)
   ├─ In-Memory (development, single-process)
   └─ Redis (production, multi-process)
```

---

## Migration from Old System

If upgrading from the old `eden.tasks.scheduler` system:

### Old Way

```python
# Old scheduler.py (incomplete)
from eden.tasks.scheduler import CronExpression, TaskScheduler
scheduler = TaskScheduler()
scheduler.schedule(daily_backup, "0 2 * * *")
```

### New Way

```python
# New EdenBroker system
@app.task.every(hours=24)
async def daily_backup():
    pass

# Or with exact time via APScheduler backend (future)
@app.task.every(cron="0 2 * * *")
async def daily_backup():
    pass
```

All functionality from the old system is now available in the new EdenBroker, with better testing and production support.

---

## API Reference

### EdenBroker

```python
class EdenBroker:
    # Properties
    periodic_tasks: list[PeriodicTask]
    result_backend: TaskResultBackend
    is_running: bool
    max_retries: int
    retry_delays: list[int]
    
    # Methods
    async def defer(task, *args, **kwargs) -> str
    async def schedule(task, delay: int, *args, **kwargs) -> str
    async def get_task_result(task_id: str) -> TaskResult | None
    async def get_dead_letter_tasks() -> list[TaskResult]
    async def startup() -> None
    async def shutdown() -> None
    
    # Decorators
    def task(self, *args, **kwargs) -> Callable
    def every(self, *, seconds=0, minutes=0, hours=0, cron=None) -> Callable
```

### TaskResult

```python
@dataclass
class TaskResult:
    task_id: str
    task_name: str
    status: str  # "success", "failed", "dead_letter", "pending"
    result: Any = None
    error: str | None = None
    error_traceback: str | None = None
    retries: int = 0
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    ttl_seconds: int = 604800
    
    def to_dict(self) -> dict[str, Any]
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskResult
```

### PeriodicTask

```python
class PeriodicTask:
    # Properties
    func: Callable
    task: Callable  # Alias
    cron: str | None
    interval: float  # Seconds
    execution_count: int
    last_error: Exception | None
    
    # Methods
    def start(self) -> None
    def stop(self) -> None
```

### TaskResultBackend

```python
class TaskResultBackend:
    async def store_result(task_id: str, result: TaskResult) -> None
    async def get_result(task_id: str) -> TaskResult | None
    async def cleanup_expired() -> int  # Returns count cleaned
    async def get_dead_letter_tasks() -> list[TaskResult]
    async def clear_dead_letter() -> int  # Returns count cleared
```

---

## Further Reading

- [Taskiq Documentation](https://taskiq-python.github.io/)
- [APScheduler Documentation](https://apscheduler.readthedocs.io/)
- [Redis Documentation](https://redis.io/docs/)
- Eden Framework [README.md](README.md)

