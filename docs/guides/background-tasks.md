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
eden worker --workers 4
```

For scheduled tasks (`.every()` or delayed tasks), you also need to run the scheduler:

```bash
eden scheduler
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

## Best Practices

- ✅ **Small Arguments**: Pass IDs (like `user_id`) instead of large objects. Let the worker fetch the data it needs.
- ✅ **Atomic Tasks**: Ensure your tasks are idempotent (safe to run multiple times if retried).
- ✅ **Redis for Production**: Always use the Redis broker in production to handle persistence and concurrency.
- ✅ **Monitor Logs**: Use `eden worker --debug` during development to see task output in real-time.
