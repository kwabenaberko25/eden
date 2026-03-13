# WebSockets 🔌

Eden provides native support for WebSockets, allowing you to build real-time, reactive applications with ease. For the best experience, we recommend using the **Native Real-time Sync** layer, but you can also manage raw sockets manually.

## Basic Usage

You can handle WebSocket connections using the `@app.websocket()` decorator.

```python
@app.websocket("/ws")
async def websocket_endpoint(websocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Message received: {data}")
```

## Connection Management

The `websocket` object provides several methods for managing the connection lifecycle.

| Method | Description |
| :--- | :--- |
| `accept()` | Accepts the incoming connection. |
| `receive_text()` | Receives a string from the client. |
| `receive_json()` | Receives and parses JSON from the client. |
| `send_text(data)` | Sends a string to the client. |
| `send_json(data)` | Sends a dictionary as JSON to the client. |
| `close(code)` | Closes the connection with an optional status code. |

---

## Real-Time ORM Sync

Eden provides automatic real-time synchronization for models marked with `__reactive__ = True`. When data changes in the database, connected WebSocket clients are notified instantly:

```python
from eden import Model

class Task(Model):
    __reactive__ = True  # Enable real-time sync
    title: str
    completed: bool

# When any client updates a task:
@app.post("/tasks/{task_id}/complete")
async def complete_task(task_id: int):
    task = await Task.get(task_id)
    task.completed = True
    await task.save()  # Automatically notifies all connected clients
    return {"completed": True}

# All connected WebSocket clients receive the update
@app.websocket("/ws/tasks")
async def tasks_sync(websocket):
    await websocket.accept()
    
    # Subscribe to task updates
    async for update in Task.__reactive__.subscribe():
        await websocket.send_json({
            "type": "task_updated",
            "task": update.to_dict()
        })
```

---

## Handling Disconnects

It's important to handle disconnections gracefully to avoid leaking resources.

```python
from starlette.websockets import WebSocketDisconnect

@app.websocket("/chat")
async def chat_endpoint(websocket):
    await websocket.accept()
    try:
        while True:
            msg = await websocket.receive_text()
            ...
    except WebSocketDisconnect:
        print("Client left the chat.")
```

---

## Real-Time Auth 🔐

WebSockets in Eden have access to the same `request.user` context as HTTP routes, provided the authentication middleware is enabled.

```python
@app.websocket("/ws")
async def secure_socket(websocket):
    await websocket.accept()
    user = websocket.scope.get("user")
    if not user or not user.is_authenticated:
        await websocket.close(code=1008)
        return
    ...
```

### Advanced Authentication

For production applications requiring user authentication, connection state recovery, and message handlers, see the [WebSocket Authentication & State Management](websocket-auth.md) guide. It covers token-based auth, cookie-based auth, maintaining session state, and production patterns like heartbeats and reconnection handling.

---

## WebSocket Router 📡

For complex applications, use the `WebSocketRouter` to organize events and rooms.

```python
from eden.websocket import WebSocketRouter

ws = WebSocketRouter(prefix="/chat")

@ws.on_connect
async def on_connect(socket, manager):
    await manager.broadcast({"event": "join", "user": "Someone joined!"})

@ws.on("message")
async def handle_message(socket, data, manager):
    # 'data' is automatically parsed from JSON
    await manager.broadcast({"event": "message", "text": data["text"]})

# Mount the router
ws.mount(app)
```


---

---

## 🔄 Real-Time ORM Sync

Eden's **Reactive Layer** automatically broadcasts database events to connected WebSocket clients. This allows for zero-configuration real-time updates.

### 1. Making a Model Reactive

Just set `__reactive__ = True` on your model. Eden handles the rest.

```python
class Task(Model):
    __reactive__ = True
    title: Mapped[str] = f()
    is_completed: Mapped[bool] = f(default=False)
```

### 2. Listening for Updates in Templates

Use the `hx-sync` attribute (via our HTMX integration) to listen for specific model updates.

#### Way 1: Reload a List
```html
<div hx-sync="tasks" 
     hx-trigger="tasks:created, tasks:deleted" 
     hx-get="/tasks/list" 
     hx-target="#task-container">
    <div id="task-container">...</div>
</div>
```

#### Way 2: Single Item Update
```html
<div id="task-@span(task.id)" 
     hx-sync="tasks:@span(task.id)" 
     hx-trigger="tasks:updated" 
     hx-get="/tasks/@span(task.id)">
    @span(task.title)
</div>
```

### 3. Manual Broadcasting

For custom events that aren't tied directly to a model save:

```python
from eden import manager

async def notify_all():
    await manager.broadcast("global-alerts", {"message": "System Maintenance!"})
```

---

## 🏫 Real-World Scenario: Live Attendance Tracker

In a School Management System, you might want a "Live Attendance" dashboard that updates instantly as students tap their ID cards.

### 1. The Model
```python
class Attendance(Model):
    __reactive__ = True  # Enable real-time broadcasting
    student_name: Mapped[str] = f()
    timestamp: Mapped[datetime] = f(default=datetime.now)
```

### 2. The Teacher's View
```html
<div class="eden-card p-6">
    <h3 class="premium-heading">Live Attendance Feed</h3>
    
    <div id="attendance-feed" 
         hx-sync="attendance" 
         hx-trigger="attendance:created" 
         hx-get="/attendance/latest-list" 
         hx-swap="afterbegin">
        <!-- New items will appear at the top automatically -->
    </div>
</div>
```

### 3. The Backend Logic (When a student taps)
```python
@app.post("/api/tap")
async def record_tap(request):
    data = await request.json()
    # Saving the model automatically triggers the WebSocket broadcast
    await Attendance.create(student_name=data['name'])
    return {"status": "ok"}
```

---

> [!TIP]
> **Performance**: Native Sync is extremely efficient and uses Redis or an in-memory bus to keep overhead minimal even with thousands of concurrent updates.

**Next Steps**: [Exception Handling](exceptions.md)
