# Background Tasks ⚙️

Eden offloads long-running or periodic processes to a background worker system powered by **Taskiq** and the **EdenBroker**.

## How it Works

Eden uses a "Broker" to manage tasks. By default, we recommend using **Redis** for the task queue.

### Configuration

```python
from eden.tasks import EdenBroker

broker = EdenBroker("redis://localhost:6379")
app.broker = broker
```

---

## Defining Tasks

Tasks are simple Python functions decorated with `@broker.task`.

```python
@broker.task
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

Eden tasks support automatic retries for flaky operations (like external APIs).

```python
@broker.task(retries=3, retry_delay=5)
async def process_payment(order_id: int):
    # If this fails, it will retry 3 times with 5s delay
    pass
```

---

## Running the Worker

To execute background tasks, you must run the task worker in a separate process or container.

```bash
eden tasks run
```

---

## Elite Pattern: Periodic Tasks & Monitoring 🕰️

Use tasks for recurring system maintenance or high-frequency data processing.

```python
from eden.tasks import schedule

@broker.task
@schedule(cron="0 0 * * *") # Every night at midnight
async def cleanup_expired_sessions():
    count = await Session.filter(expires_at__lt=datetime.now()).delete()
    print(f"Cleaned up {count} sessions.")
```

### Task Monitoring

Eden workers emit metrics that can be scraped by Prometheus or viewed in the Eden Forge UI.

**Next Steps**: [Integrated Services](services.md)
