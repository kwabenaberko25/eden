# Background Tasks ⚙️

Eden offloads long-running or periodic processes to a background worker system powered by **Taskiq** and the **EdenBroker**.

## How it Works

Eden uses a "Broker" to manage tasks. By default, we recommend using **Redis** for the task queue.

### Configuration

### Configuration

Eden's entry point is the `broker` instance on the `app` object.

```python
from eden import Eden
from eden.tasks import create_broker

app = Eden()

# Development (In-memory)
app.broker = create_broker()

# Production (Redis)
app.broker = create_broker(redis_url="redis://localhost:6379")
```


---

## Defining Tasks

Tasks are simple Python functions decorated with `@app.broker()`.

```python
@app.broker()
async def send_welcome_email(user_id: int):
    user = await User.get(id=user_id)
    # ... expensive email logic ...
    print(f"Welcome email sent to {user.email}")
```


---

## Invoking Tasks

Tasks can be executed immediately or scheduled for the background.

```python
# Runs in the current process (Synchronous)
result = await send_welcome_email(user.id)

# Offloads to the background (Returns a TaskiqResult object)
task = await send_welcome_email.kiq(user.id)
print(f"Task ID: {task.task_id}")

# Wait for result (optional)
result = await task.wait_result()
```

### `.kiq()` Parameters

| Parameter | Description |
| :--- | :--- |
| `task_id` | Manual ID for tracking. |
| `schedule` | Delay or cron string. |
| `labels` | Metadata for the worker. |

---

## Error Handling & Retries 🔁

Eden tasks support automatic retries for flaky operations. Note that retry parameters are passed to the decorator.

```python
@app.broker(retries=3, retry_delay=5)
async def process_payment(order_id: int):
    # If this fails, it will retry 3 times with 5s delay
    pass
```


---

To execute background tasks, you must run the task worker:

```bash
eden worker --workers 2
```

For scheduled/periodic tasks, you also need the scheduler:

```bash
eden scheduler
```


---

## Elite Pattern: Periodic Tasks 🕰️

Use `.every()` for recurring system maintenance.

```python
@app.broker.every(hours=24)
async def cleanup_expired_sessions():
    # Eden handles the background loop
    ...

@app.broker.every(cron="0 0 * * *") # Every night at midnight
async def daily_report():
    ...
```


### Task Monitoring

Eden workers emit metrics that can be scraped by Prometheus or viewed in the Eden Forge UI.

**Next Steps**: [Integrated Services](services.md)
