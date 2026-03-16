# Real-time Synchronization & WebSockets

> **Build Dynamic, Live-Updating Applications with Eden Sync**

The Eden framework provides a two-pronged approach to real-time features:

1. **Eden Sync (ORM-to-UI)**: Automatic WebSocket broadcasts whenever your database models change.
2. **Low-Level WebSockets**: Robust connection management for custom patterns like chat or live dashboards.

---

## 1. Eden Sync: Automatic UI Updates

Eden Sync eliminates the complexity of manual WebSocket management. By simply adding a flag to your ORM models, Eden will broadcast events (`created`, `updated`, `deleted`) to the frontend automatically.

### Enabling Sync on Models

To make a model "reactive," set the `__reactive__` attribute to `True`.

```python
from eden.db import Model

class Task(Model):
    __tablename__ = "tasks"
    __reactive__ = True  # <--- Activating Eden Sync
    
    title = Column(String)
    is_completed = Column(Boolean, default=False)
```

### Granular Sync Channels

By default, sync events are broadcast to:

- `tasks` (the table name)
- `tasks:{id}` (specific instance)

You can define custom channels (e.g., per-tenant or per-user) by implementing `get_sync_channels`:

```python
class Task(Model):
    ...
    def get_sync_channels(self) -> list[str]:
        # Only broadcast to the tenant who owns this task
        return [f"tenant:{self.tenant_id}:tasks"]
```

### The Frontend: `eden-sync`

Eden's frontend runtime (included via `@eden_scripts`) contains an Alpine.js and HTMX extension called `eden-sync` that listens for these events. Use the `hx-sync` attribute to subscribe to a model's channel.

```html
<div x-data="{ tasks: [] }" 
     hx-sync="tasks" 
     @sync:created="tasks.push($event.detail.data)"
     @sync:updated="/* handle update */"
     @sync:deleted="tasks = tasks.filter(t => t.id !== $event.detail.data.id)">
    
    <template x-for="task in tasks">
        <div x-text="task.title"></div>
    </template>
</div>
```

---

## 2. Global WebSocket Management

For custom features like chat, Eden provides a unified `ConnectionManager`.

### The WebSocket Router

Define WebSocket endpoints using the `@app.websocket` decorator.

```python
from eden import Request, WebSocketDisconnect
from eden.websocket import connection_manager

@app.websocket("/ws/chat/{room_id}")
async def chat_ws(websocket, room_id: str):
    user = await get_current_user(websocket)
    
    # 1. Accept and register the connection
    await connection_manager.connect(websocket, user_id=user.id)
    
    # 2. Join a specific room (channel)
    await connection_manager.subscribe(websocket, f"chat:{room_id}")
    
    try:
        while True:
            # 3. Handle incoming messages
            data = await websocket.receive_json()
            
            # 4. Broadcast to the room
            await connection_manager.broadcast({
                "user": user.name,
                "message": data["text"]
            }, channel=f"chat:{room_id}")
            
    except WebSocketDisconnect:
        # 5. Automatic cleanup on disconnect
        await connection_manager.disconnect(websocket)
```

---

## 3. Tutorial: Building a Premium Chat App

Let's build a real-time chat dashboard with premium aesthetics.

### Step 1: The Model

Enable sync so we can track "Online" status or "Last Message" globally if needed.

```python
class Message(Model):
    __tablename__ = "messages"
    __reactive__ = True
    
    room_id = Column(String, index=True)
    sender_id = Column(Integer)
    content = Column(Text)
```

### Step 2: The Template

Use Alpine.js and HTMX together for an elite experience.

```html
@extends("layouts/base")

@section("content")
<div class="chat-container glass h-[600px] flex flex-col"
     x-data="{ messages: [], text: '' }"
     eden-sync="messages"
     @sync:created="messages.push($event.detail.data)">
    
    <!-- Header -->
    <div class="p-4 border-b border-white/10 flex justify-between">
        <h2 class="text-xl font-bold">Project Alpha</h2>
        <span class="text-xs text-emerald-400">● Live</span>
    </div>

    <!-- Messages Area -->
    <div class="flex-1 overflow-y-auto p-4 space-y-4" id="message-list">
        <template x-for="msg in messages">
            <div class="flex flex-col" :class="msg.sender_id == current_user_id ? 'items-end' : 'items-start'">
                <div class="px-4 py-2 rounded-2xl max-w-[80%]"
                     :class="msg.sender_id == current_user_id ? 'bg-emerald-600 text-white' : 'bg-white/10'">
                    <p x-text="msg.content"></p>
                </div>
                <span class="text-[10px] text-slate-500 mt-1" x-text="msg.created_at | time_ago"></span>
            </div>
        </template>
    </div>

    <!-- Input Bar -->
    <div class="p-4 bg-white/5 border-t border-white/10">
        <form hx-post="/chat/send" hx-swap="none" @submit="text = ''">
            <div class="flex gap-2">
                <input type="text" name="content" x-model="text"
                       class="flex-1 bg-black/20 border border-white/10 rounded-lg px-4 py-2 focus:border-emerald-500 outline-none"
                       placeholder="Type your message...">
                <button class="bg-emerald-600 hover:bg-emerald-500 px-6 py-2 rounded-lg transition">
                    Send
                </button>
            </div>
        </form>
    </div>
</div>
@endsection
```

### Step 3: The Handler

Handle the form post and let `Eden Sync` take care of the WebSocket broadcast.

```python
@app.post("/chat/send")
async def send_message(request):
    form = await request.form()
    
    # Saving the model triggers the 'after_insert' sync listener
    await Message.create(
        content=form["content"],
        sender_id=request.user.id,
        room_id="general"
    )
    
    return Response(status_code=204) # No content needed, UI updates via Sync
```

---

## 4. Performance & Scalability

- **Context-Aware Broadcasts**: Use `connection_manager.send_to_user(user_id, msg)` to send notification-style alerts to all devices of a single user.
- **Graceful Disconnects**: Eden automatically removes dead connections from the manager to prevent memory leaks.
- **Background Tasks**: You can trigger broadcasts from background tasks (Taskiq) to notify users when long-running jobs are finished.

```python
@app.task
async def export_data(user_id: str):
    # Perform heavy work...
    await connection_manager.send_to_user(user_id, {
        "event": "export_complete",
        "url": "/downloads/report.pdf"
    })
```
