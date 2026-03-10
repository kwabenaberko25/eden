# WebSockets 🔌

Eden provides native support for WebSockets, allowing you to build real-time, reactive applications with ease.

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

## Elite Pattern: Real-Time Notifications 🔔

Combine WebSockets with Background Tasks to send instant UI updates.

```python
@broker.task
async def notify_user(user_id: int, message: str):
    # Retrieve the manager from app state
    manager = app.state.ws_manager
    await manager.send_to_user(user_id, message)

# In your route
@app.post("/events")
async def create_event(request):
    await notify_user.kiq(request.user.id, "New event created!")
    return {"status": "ok"}
```

**Next Steps**: [Exception Handling](exceptions.md)
