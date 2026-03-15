# Background Workers in Eden

Eden uses **Taskiq** for robust asynchronous task processing. This allows you to offload heavy computations, email sending, or scheduled maintenance to separate processes.

## 1. Defining Tasks

Use the `@app.task()` decorator on your functions.

```python
# app/tasks.py
from eden import Eden

app = Eden()

@app.task()
async def process_video(video_id: str):
    print(f"Processing video {video_id}...")
    # Your heavy logic here
```

## 2. Configuration

In production, you should use **Redis** as the broker. In development, Eden defaults to an `InMemoryBroker`.

```python
# .env
REDIS_URL=redis://localhost:6379
```

## 3. Running the Worker

To start processing tasks, run the Taskiq worker. You need to point it to your Eden application's broker.

```bash
# Run one worker process
taskiq worker app.main:app.broker
```

### With Hot Reload (Development)
```bash
taskiq worker app.main:app.broker --reload
```

## 4. Periodic Tasks (Schedules)

Eden supports periodic tasks via `@app.task.every()`.

```python
@app.task.every(minutes=10)
async def cleanup_temp_files():
    print("Cleaning up...")
```

To run these schedules, you need the **Taskiq Scheduler** (or rely on Eden's built-in startup scheduler for single-instance setups).

## 5. Monitoring & Retries

Eden automatically retries failed tasks with **exponential backoff**:
- Retry 1: 1s delay
- Retry 2: 2s delay
- Retry 3: 4s delay
- Retry 4: 8s delay
- Retry 5: 16s delay

You can view permanently failed tasks via `app.broker.get_dead_letter_tasks()`.
