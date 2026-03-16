# Background Tasks ⚙️

Eden offloads long-running or periodic processes to a background worker system powered by **Taskiq** and the **EdenBroker**. This enables you to maintain a fast, responsive UI by deferring heavy computations, email sending, or data processing to a dedicated worker.

## Configuration

Eden uses a "Broker" to manage the task queue. We recommend **Redis** for production and an **In-Memory** broker for local development.

```python
from eden import Eden, create_broker

app = Eden()

# Development: In-memory (no extra setup)
app.task = create_broker()

# Production: Redis (requires taskiq-redis)
app.task = create_broker(redis_url="redis://localhost:6379")
```

## Defining & Invoking Tasks

Tasks are simple Python functions decorated with `@app.task()`.

### 1. Define the Task
```python
@app.task()
async def send_welcome_email(user_id: int):
    user = await User.get(id=user_id)
    # ... expensive logic ...
    print(f"Welcome email sent to {user.email}")
```

### 2. Invoke the Task
There are two ways to trigger a task:

#### The `.kiq()` method (Standard)
```python
# Triggers the task in the background worker
await send_welcome_email.kiq(user.id)
```

#### The `defer()` helper (Clean API)
```python
# A more readable way to send a task to the queue
await app.task.defer(send_welcome_email, user.id)
```

## Periodic & Scheduled Tasks 🕰️

Eden makes scheduling recurring tasks a first-class citizen with the `.every()` decorator.

```python
# Every 1 minute
@app.task.every(minutes=1)
async def check_alerts():
    ...

# Every night at midnight (Standard Cron)
@app.task.every(cron="0 0 * * *")
async def daily_report():
    ...

# Every 30 seconds
@app.task.every(seconds=30)
async def heartbeat():
    ...
```

### Delaying Tasks
To run a task after a specific delay (in seconds):

```python
# Remind the user in 1 hour (3600 seconds)
await app.task.schedule(send_reminder, delay=3600, user_id=42)
```

## Running the Workers

To execute your background tasks, you must run the Eden worker process in a separate terminal:

```bash
# Run 4 parallel worker processes
eden tasks worker --workers 4
```

For scheduled tasks (`.every()` or delayed tasks), you also need to run the scheduler:

```bash
eden tasks scheduler
```

## Lifecycle & Synergies

### The "Killer" Loop: Task -> WebSocket
A common pattern in Eden is to kick off a task and have it notify the user via WebSockets when finished.

```python
@app.task()
async def process_video(video_id: int, user_id: int):
    # 1. Heavy processing...
    await do_processing(video_id)
    
    # 2. Notify the user instantly via WebSocket
    from eden.websocket import connection_manager
    await connection_manager.broadcast(
        {"event": "video_ready", "id": video_id},
        room=f"user_{user_id}"
    )
```

---

## 🛡️ Error Handling & Retries

Background tasks can sometimes fail due to external network issues or database locks. Eden allows you to define retry policies to make your tasks resilient.

### Automatic Retries
```python
@app.task(
    retries=3,          # Retry up to 3 times
    retry_on=[TimeoutError, NetworkError], # Only retry on these errors
    delay=5             # Wait 5 seconds between retries
)
async def fetch_external_data(api_url: str):
    # Logic...
```

### Manual Retry Logic
You can also trigger a retry manually from within the task based on custom logic.

```python
from taskiq import TaskiqRetry

@app.task()
async def provision_server(server_id: int):
    status = await check_status(server_id)
    if status != "ready":
        # Raise this to put the task back in the queue
        raise TaskiqRetry("Server not ready yet, retrying...")
```

---

## 📊 Task Results & Monitoring

Sometimes you need to know what a task returned or if it succeeded.

### Fetching Results
To get the return value of a task, ensure you use the Redis broker as it stores task results.

```python
# 1. Dispatch the task
task_handle = await app.task.defer(heavy_calc, 10, 20)

# 2. Wait for the result (in a route or another task)
result = await task_handle.wait_result(timeout=10.0)
print(f"Computed value: {result.return_value}")
```

### Result Persistence
By default, results are kept for 24 hours in Redis. You can configure this in your `EDEN_SETTINGS` to store them longer for auditing.

---

## 🛠️ Advanced: Progress Tracking
For very long tasks, you can report progress that the UI can pick up via WebSockets.

```python
@app.task()
async def import_csv(file_id: int):
    rows = await load_csv(file_id)
    total = len(rows)
    
    for i, row in enumerate(rows):
        await process_row(row)
        
        # Report progress every 10%
        if i % (total // 10) == 0:
            await app.ws.broadcast(
                {"event": "import_progress", "percent": (i/total)*100},
                room=f"file_{file_id}"
            )
```

---

## Best Practices

- ✅ **Small Arguments**: Pass IDs (like `user_id`) instead of large objects. Let the worker fetch the data it needs.
- ✅ **Atomic Tasks**: Ensure your tasks are idempotent (safe to run multiple times if retried).
- ✅ **Redis for Production**: Always use the Redis broker in production to handle persistence and concurrency.
- ✅ **Monitor Logs**: Use `eden worker --debug` during development to see task output in real-time.
- ✅ **Timeout Control**: Use `timeout` in your `.kiq()` calls to prevent tasks from hanging forever.

---

**Next Steps**: [Advanced SaaS & Multi-Tenancy](tenancy.md)
