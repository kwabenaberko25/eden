# WebSockets & Real-Time 🔌

Eden provides a high-level, event-driven WebSocket system that makes real-time communication as simple as standard HTTP routing. By combining the `WebSocketRouter` with Eden's **Reactive ORM**, you can build live-updating dashboards and chat systems with almost zero boilerplate.

## The Event-Driven Router: `WebSocketRouter`

For production applications, we recommend using the `WebSocketRouter`. It allows you to organize your real-time logic into specialized event handlers.

```python
from eden.websocket import WebSocketRouter

# Initialize router with a prefix
chat_ws = WebSocketRouter(prefix="/ws/chat")

@chat_ws.on_connect
async def on_connect(socket, manager):
    """Called when any client connects."""
    # manager is the room-aware ConnectionManager
    await manager.broadcast({"event": "sys", "msg": "A user joined"}, room="lobby")

@chat_ws.on("chat_message")
async def handle_chat(socket, data, manager):
    """
    Handle the 'chat_message' event.
    'data' is automatically parsed from the incoming JSON.
    """
    room = data.get("room", "lobby")
    await manager.broadcast({
        "event": "chat_message",
        "user": socket.user.name,
        "text": data["text"]
    }, room=room)

# Mount the router to your Eden app
chat_ws.mount(app)
```

### Protocol & Message Format
The `WebSocketRouter` expects JSON messages with an `event` key. If no `event` key is found, it defaults to the `"message"` event.

```json
{
  "event": "chat_message",
  "text": "Hello Eden!",
  "room": "lobby"
}
```

## Room Management: `ConnectionManager`

The `manager` instance provided to your handlers is a powerful tool for targeting specific groups of users.

| Method | Description |
| :--- | :--- |
| `broadcast(message, room="default")` | Sends to everyone in the specified room. |
| `send_to(socket, message)` | Sends to a specific individual connection. |
| `count(room="default")` | Returns the number of active users in a room. |
| `rooms` | A property returning all active room names. |

## 🔄 Reactive ORM: Automating the UI

Eden's "Killer" real-time feature is its **Reactive Layer**. When a model is marked as reactive, Eden automatically broadcasts changes to a dedicated WebSocket channel.

### 1. Enable Reactivity
```python
class Task(Model):
    __reactive__ = True  # Automatically triggers broadcasts on save/delete
    title: str
    is_done: bool = False
```

### 2. Frontend Integration (HTMX + WebSockets)
Eden ships with a custom HTMX extension to handle these model broadcasts without you writing a single line of JS.

```html
<div hx-ext="ws" ws-connect="/ws/tasks/updates">
    <div id="task-list" 
         hx-get="/tasks/fragment" 
         hx-trigger="tasks:updated, tasks:created from:body">
        @include("partials/tasks")
    </div>
</div>
```

> [!NOTE]
> When `Task.save()` is called in the backend, Eden broadcasts a `tasks:updated` event. The HTMX extension captures this and triggers the `hx-get` to refresh the list surgically.

## Security & Persistence 🔐

### Authentication
Eden's `WebSocketRouter` automatically integrates with your `SessionMiddleware`. The `socket` object in your handlers has a `.user` attribute populated if the user is logged in.

```python
@ws.on_connect
async def secure_connect(socket, manager):
    if not socket.user.is_authenticated:
        await socket.close(code=1008)  # Policy Violation
        return
```

### Multi-Tenancy
When using Eden's built-in Multi-Tenancy, you should always include the `tenant_id` in your room names to ensure isolation.

```python
@ws.on("message")
async def handle_tenant_msg(socket, data, manager):
    # Isolated by tenant_id
    room = f"tenant_{socket.user.tenant_id}_chat"
    await manager.broadcast(data, room=room)
```

## Best Practices

- ✅ **Use Rooms**: Never broadcast globally if you can target a specific room.
- ✅ **JSON Always**: Stick to JSON for your WebSocket protocol to leverage automatic parsing.
- ✅ **Graceful Handling**: The `WebSocketRouter` handles `WebSocketDisconnect` automatically, but you can use `@ws.on_disconnect` for cleanup (e.g., status updates).
- ✅ **Reactive synergy**: Use the ORM's `__reactive__` flag for state synchronization rather than manual broadcasting where possible.
