# ⚡ Real-time Synchronization & WebSockets

**Experience the "Live-Wired" SaaS. Eden provides a high-performance synchronization engine that bridges your database models directly to your UI, along with a robust WebSocket infrastructure for custom real-time patterns.**

---

## 🧠 Conceptual Overview

Eden employs a dual-layer approach to real-time communication:

1.  **Eden Sync (High-Level)**: Automatic, event-driven broadcasts triggered by ORM model changes. Ideal for lists, status indicators, and live dashboards.
2.  **WebSocket Engine (Low-Level)**: A distributed, security-hardened `ConnectionManager` for custom bi-directional logic like chat, gaming, or collaborative editing.

### The Real-time Pipeline

```mermaid
graph LR
    A["DB Change: Project Updated"] --> B["Eden Sync Hub"]
    B --> C["Redis / Distributed Backend"]
    C --> D["Worker 1: WebSocket"]
    C --> E["Worker 2: WebSocket"]
    D --> F["User A: Browser UI"]
    E --> G["User B: Browser UI"]
```

---

## 🛠️ Eden Sync: Reactive UI with Zero Boilerplate

Eden Sync eliminates the need for manual WebSocket orchestration. By marking a model as reactive, the framework will automatically broadcast `created`, `updated`, and `deleted` events to all connected clients.

### 1. Activating the Model
Simply set `__reactive__ = True` in your model class.

```python
from eden.db import Model, f

class Task(Model):
    __tablename__ = "tasks"
    __reactive__ = True  # <--- Core Sync Activation
    
    title: str = f()
    is_completed: bool = f(default=False)
    tenant_id: int = f()

    def get_sync_channels(self) -> list[str]:
        # Isolate broadcasts to the specific tenant
        return [f"tenant:{self.tenant_id}:tasks"]
```

### 2. The Frontend: `hx-sync`
Using Eden's frontend runtime (included via `@eden_scripts`), you can subscribe to these events using HTMX and Alpine.js.

```html
<div x-data="{ tasks: [] }" 
     hx-sync="tenant:123:tasks" 
     @sync:created="tasks.push($event.detail.data)"
     @sync:deleted="tasks = tasks.filter(t => t.id !== $event.detail.data.id)">
    
    <template x-for="task in tasks">
        <div class="p-2 border-b border-white/5 flex justify-between">
            <span x-text="task.title"></span>
            <span class="text-xs opacity-50" x-text="task.created_at | time_ago"></span>
        </div>
    </template>
</div>
```

---

## 🏰 The `ConnectionManager`: Enterprise WebSocket Infrastructure

For custom bi-directional logic, use the `connection_manager`. It is designed for security (CSRF/Origin checks) and distributed scale (worker synchronization).

### Custom WebSocket Endpoint
```python
from eden.websocket import connection_manager

@app.websocket("/ws/project/{project_id}")
async def project_ws(websocket, project_id: str):
    # 1. Accept and Validate (Origin & CSRF checked automatically)
    await connection_manager.connect(websocket, user_id=request.user.id)
    
    # 2. Subscribe to a specific channel
    await connection_manager.subscribe(websocket, f"project:{project_id}")
    
    try:
        while True:
            # 3. Handle messages
            data = await websocket.receive_json()
            
            # 4. Broadcast to the channel (syncs across all worker instances!)
            await connection_manager.broadcast(
                {"event": "cursor_move", "user": request.user.name, "coords": data},
                channel=f"project:{project_id}"
            )
    except WebSocketDisconnect:
        await connection_manager.disconnect(websocket)
```

---

## ⚡ Elite Patterns

### 1. The "Toast" System
Broadcast global notifications directly to a user's browser from anywhere in your backend (views, tasks, or CLI).

```python
# From a view or background task
await connection_manager.send_to_user(target_user_id, {
    "type": "notification",
    "title": "Build Complete",
    "message": "Your project is now live!",
    "intent": "success"
})
```

### 2. Distributed Mode (Scaling Out)
If you run multiple server instances behind a load balancer, connect them via Redis to ensure a broadcast from Worker A reaches a user connected to Worker B.

```python
# During app startup
from eden.core.backends.redis import RedisBackend
from eden.websocket import connection_manager

backend = RedisBackend(url="redis://localhost:6379")
await connection_manager.set_distributed_backend(backend)
```

### 3. Graceful Shutdown
Eden ensures all connections are notified and closed cleanly during server shutdown to prevent client-side "unclean hang" errors.

---

## 📄 API Reference

### `ConnectionManager` Methods

| Method | Parameters | Description |
| :--- | :--- | :--- |
| `broadcast` | `message, channel, exclude` | Sends to all subscribers of a channel. Syncs across workers if distributed. |
| `send_to_user` | `user_id, message` | Sends to *all* active sockets owned by a specific user ID. |
| `subscribe` | `websocket, channel` | Adds a socket to a named room/channel. |
| `count` | - | Returns number of active connections on the current worker. |

### Eden Sync Events (Browser)

| Event Name | Data Payload | Description |
| :--- | :--- | :--- |
| `@sync:created` | `detail.data` | Triggered when a reactive model is inserted. |
| `@sync:updated` | `detail.data` | Triggered when a reactive model is updated. |
| `@sync:deleted` | `detail.data` | Triggered when a reactive model is deleted. |

---

## 💡 Best Practices

1.  **Security First**: Always use `require_role` or custom auth checks inside your `@app.websocket` handler before calling `connection_manager.connect()`.
2.  **Isolate Channels**: Use scoped channels like `tenant:{id}:model` instead of global ones to prevent data leakage.
3.  **JSON Standard**: Always broadcast dicts/JSON for interoperability with Alpine.js and other frontend frameworks.
4.  **Heartbeats**: Eden handles basic connection liveness, but for mission-critical apps, implement a custom "Ping" logic within your `while True` loop.

---

**Next Steps**: [Asset Management & Pipelines](assets.md)
