# WebSocket Authentication & State Recovery 🔐

Eden provides secure WebSocket connections with built-in authentication, reconnection support, and state recovery. This guide covers the **AuthenticatedWebSocket** class for production-ready real-time applications.

> **New to WebSockets?** Start with [Basic WebSocket Usage](websockets.md) first, then return here for advanced patterns.

---

## Overview

### When to Use AuthenticatedWebSocket

**Use this when you need:**
- 🔒 User authentication for WebSocket connections
- 🔄 Automatic reconnection with state recovery
- 💬 Room-based messaging with user filtering
- 🛡️ Secure token or session-based auth
- 📊 Connection state management

**Basic WebSocketRouter** is simpler but doesn't include auth or state recovery.

### Architecture

```
┌─────────────────────────────────────────┐
│      AuthenticatedWebSocket             │
├─────────────────────────────────────────┤
│ • User authentication (token/cookie)    │
│ • Connection state tracking             │
│ • Message handler routing               │
│ • Auto-reconnection support             │
└─────────────────────────────────────────┘
         ↓ manages ↓
┌─────────────────────────────────────────┐
│      ConnectionManager                  │
├─────────────────────────────────────────┤
│ • Room-based connection tracking        │
│ • Broadcast to group                    │
│ • Per-user broadcast filtering          │
└─────────────────────────────────────────┘
         ↓ stores ↓
┌─────────────────────────────────────────┐
│      ConnectionState                    │
├─────────────────────────────────────────┤
│ • user_id: str                          │
│ • room: str                             │
│ • connected_at: str (ISO timestamp)     │
│ • metadata: Dict[str, Any]              │
└─────────────────────────────────────────┘
```

---

## 1. Connection Types & Authentication

### Token-Based Authentication

Authenticate using a token passed in the query string.

```python
from eden import Eden
from eden.websocket.auth import AuthenticatedWebSocket, AuthenticationError

app = Eden(__name__)

@app.websocket("/ws/chat/{room_id:int}")
async def chat_connection(websocket: AuthenticatedWebSocket, room_id: int):
    try:
        # Authenticate using token from query string
        # Connect like: ws://localhost:8000/ws/chat/5?token=abc123
        user = await websocket.authenticate_with_token(token_name="token")
        
        # Accept the connection
        await websocket.accept()
        
        # Store room
        websocket.room = f"chat_{room_id}"
        
        # Notify others
        await websocket.broadcast_message(
            f"👋 {user.name} joined the chat"
        )
        
        # Handle messages
        await websocket.handle_messages()
        
    except AuthenticationError as e:
        await websocket.close(code=1008)  # Policy Violation
        return
```

**Client-side (JavaScript/HTML):**

```html
<script>
// Get token from page or API call
const token = await fetchUserToken();

// Connect with token
const ws = new WebSocket(
    `ws://localhost:8000/ws/chat/5?token=${token}`
);

ws.onopen = () => console.log("Connected");
ws.onmessage = (event) => console.log(event.data);
ws.onerror = (error) => console.error(error);
</script>
```

### Cookie-Based Authentication

Authenticate using the session cookie (requires SessionMiddleware).

```python
@app.websocket("/ws/notifications")
async def notifications(websocket: AuthenticatedWebSocket):
    try:
        # Authenticate from session cookie (if logged in)
        user = await websocket.authenticate_with_cookie()
        
        await websocket.accept()
        
        # Send initial notification
        await websocket.send_json({
            "type": "status",
            "message": f"Welcome back, {user.name}!"
        })
        
        # Handle messages
        await websocket.handle_messages()
        
    except AuthenticationError:
        # Not logged in - reject connection
        await websocket.close(code=1008)
```

### Custom Token Validation

Override the token validation for JWT, OAuth, or custom schemes:

```python
class MyAuthenticatedWebSocket(AuthenticatedWebSocket):
    """Custom WebSocket with JWT validation."""
    
    async def _validate_token(self, token: str) -> Optional[Any]:
        """Validate JWT token and return user."""
        import jwt
        
        try:
            # Decode JWT
            payload = jwt.decode(
                token, 
                self.app.config.get("SECRET_KEY"),
                algorithms=["HS256"]
            )
            
            # Load user from database
            from app.models import User
            user = await User.get(id=payload["user_id"])
            return user
            
        except (jwt.InvalidTokenError, jwt.ExpiredSignatureError):
            return None

# Use in routes
@app.websocket("/ws/data")
async def data_stream(websocket: MyAuthenticatedWebSocket):
    user = await websocket.authenticate_with_token()
    await websocket.accept()
    # ...
```

---

## 2. Message Handling

### Handler Decorator Pattern

Register handlers for specific message types:

```python
@app.websocket("/ws/chat/{room_id:int}")
async def chat(websocket: AuthenticatedWebSocket, room_id: int):
    user = await websocket.authenticate_with_token()
    await websocket.accept()
    
    # Register message handlers
    @websocket.on_message("chat")
    async def handle_chat(socket, data):
        """Handle chat messages."""
        message = data.get("text", "")
        
        if not message or len(message) > 1000:
            await socket.send_json({
                "type": "error",
                "message": "Message too long or empty"
            })
            return
        
        # Broadcast to room
        broadcast_data = {
            "type": "chat",
            "user": socket.user.name,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        # Get connection manager
        from eden.websocket.auth import connection_manager
        await connection_manager.broadcast_to_room(
            f"chat_{room_id}",
            broadcast_data,
            exclude_user=str(socket.user.id)  # Don't echo back to sender
        )
    
    @websocket.on_message("typing")
    async def handle_typing(socket, data):
        """Handle 'user is typing' indicator."""
        await socket.send_json({
            "type": "typing",
            "user": socket.user.name
        })
    
    # Main message loop
    await websocket.handle_messages()
```

**Client sends:**

```javascript
// Send chat message
ws.send(JSON.stringify({
    type: "chat",
    text: "Hello everyone!"
}));

// Send typing indicator
ws.send(JSON.stringify({
    type: "typing"
}));
```

### Server Broadcasts to Client

```python
@websocket.on_message("request_users")
async def handle_request_users(socket, data):
    """Send list of users in room."""
    from eden.websocket.auth import connection_manager
    
    room_info = connection_manager.get_room_info(f"chat_{room_id}")
    
    await socket.send_json({
        "type": "users",
        "count": room_info["user_count"],
        "users": room_info["users"]
    })
```

---

## 3. State Recovery & Reconnection

### Saving Connection State

Persist connection state so users can reconnect and resume:

```python
@app.websocket("/ws/chat/{room_id:int}")
async def chat(websocket: AuthenticatedWebSocket, room_id: int):
    user = await websocket.authenticate_with_token()
    await websocket.accept()
    
    websocket.room = f"chat_{room_id}"
    
    # Check if reconnecting from previous session
    previous_state_json = websocket.query_params.get("state")
    if previous_state_json:
        try:
            await websocket.restore_state(previous_state_json)
            await websocket.send_json({
                "type": "reconnected",
                "message": "Session resumed"
            })
        except Exception as e:
            print(f"Failed to restore state: {e}")
    
    # Register handlers...
    
    try:
        await websocket.handle_messages()
    finally:
        # Save state before closing
        state_json = await websocket.save_state()
        
        # Send to client so it can reconnect
        await websocket.send_json({
            "type": "disconnecting",
            "state": state_json,
            "reconnect_in": 5  # seconds
        })
```

### Client Reconnection Logic

```html
<script>
let reconnectAttempts = 0;
const MAX_RECONNECT = 5;
let savedState = null;

function connectWebSocket() {
    let url = "ws://localhost:8000/ws/chat/5?token=" + token;
    
    // Include previous state if reconnecting
    if (savedState) {
        url += `&state=${encodeURIComponent(savedState)}`;
    }
    
    const ws = new WebSocket(url);
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.type === "disconnecting") {
            // Server is closing - save state for reconnection
            savedState = data.state;
            
            // Reconnect after delay
            setTimeout(() => {
                reconnectAttempts++;
                if (reconnectAttempts < MAX_RECONNECT) {
                    connectWebSocket();
                }
            }, data.reconnect_in * 1000);
        }
    };
    
    ws.onclose = () => {
        // Unexpected disconnect - try reconnecting
        if (reconnectAttempts < MAX_RECONNECT) {
            setTimeout(connectWebSocket, 2000);
        }
    };
}

// Initial connection
connectWebSocket();
</script>
```

---

## 4. Production Patterns

### Connection Limits per User

Prevent a user from opening unlimited connections:

```python
from eden.websocket.auth import connection_manager

MAX_CONNECTIONS_PER_USER = 3

@app.websocket("/ws/data")
async def data_stream(websocket: AuthenticatedWebSocket):
    user = await websocket.authenticate_with_token()
    
    # Count user's connections across all rooms
    user_connections = sum(
        len([ws for ws in connections 
             if ws.user and ws.user.id == user.id])
        for connections in connection_manager.rooms.values()
    )
    
    if user_connections >= MAX_CONNECTIONS_PER_USER:
        await websocket.close(code=1008)  # Policy Violation
        return
    
    await websocket.accept()
    await connection_manager.add_connection(websocket, "data")
    
    try:
        await websocket.handle_messages()
    finally:
        await connection_manager.remove_connection(websocket)
```

### Heartbeat / Keep-Alive

Detect disconnected clients and clean up:

```python
import asyncio

@app.websocket("/ws/realtime")
async def realtime(websocket: AuthenticatedWebSocket):
    user = await websocket.authenticate_with_token()
    await websocket.accept()
    
    # Heartbeat task
    async def send_heartbeat():
        while websocket._active:
            try:
                await websocket.send_json({"type": "ping"})
                await asyncio.sleep(30)  # Every 30 seconds
            except Exception:
                break
    
    # Start heartbeat in background
    heartbeat_task = asyncio.create_task(send_heartbeat())
    
    try:
        await websocket.handle_messages()
    finally:
        heartbeat_task.cancel()
        await websocket.close()
```

### Error Handling

```python
from eden.websocket.auth import (
    AuthenticatedWebSocket, 
    AuthenticationError, 
    ConnectionError
)

@app.websocket("/ws/secure")
async def secure(websocket: AuthenticatedWebSocket):
    try:
        user = await websocket.authenticate_with_token()
    except AuthenticationError as e:
        # Invalid token
        await websocket.close(
            code=1008,
            reason="Authentication failed"
        )
        return
    except Exception as e:
        # Other errors during auth
        await websocket.close(code=1011)  # Server error
        return
    
    await websocket.accept()
    
    try:
        await websocket.handle_messages()
    except ConnectionError as e:
        print(f"Connection error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
        await websocket.close(code=1011)
```

---

## 5. Production Deployment

### Load Testing

Test connection limits and message throughput:

```bash
# Using websocket-client library
pip install websocket-client

python load_test.py --url ws://localhost:8000/ws/chat/1 \
                    --token YOUR_TOKEN \
                    --clients 100 \
                    --duration 60
```

### Monitoring

Track active connections and room usage:

```python
from eden.websocket.auth import connection_manager

@app.get("/admin/websocket-stats")
async def websocket_stats(request):
    """Get WebSocket connection statistics."""
    total_connections = sum(
        len(connections)
        for connections in connection_manager.rooms.values()
    )
    
    return {
        "total_connections": total_connections,
        "active_rooms": len(connection_manager.rooms),
        "rooms": {
            room: {
                "connections": len(connections),
                "users": list(set(str(ws.user.id) for ws in connections if ws.user))
            }
            for room, connections in connection_manager.rooms.items()
        }
    }
```

### Scaling Across Multiple Instances

For multiple servers, use Redis for shared state:

```python
import redis

redis_client = redis.Redis(host="localhost", port=6379)

async def broadcast_to_room(room: str, message: dict, exclude_user: str = None):
    """Broadcast to room across all server instances."""
    # Publish to Redis for other servers
    redis_client.publish(
        f"room:{room}",
        json.dumps({
            "message": message,
            "exclude_user": exclude_user
        })
    )
    
    # Also broadcast locally
    from eden.websocket.auth import connection_manager
    await connection_manager.broadcast_to_room(
        room, 
        message, 
        exclude_user
    )
```

---

## API Reference

### AuthenticatedWebSocket

| Method | Signature | Returns | Purpose |
|--------|-----------|---------|---------|
| `authenticate_with_token()` | `token_name: str = "token"` | `User` | Auth via query param token |
| `authenticate_with_cookie()` | none | `User` | Auth via session cookie |
| `accept()` | `subprotocol: str = None` | `None` | Accept the connection |
| `send_json()` | `data: Dict` | `None` | Send JSON message |
| `send_text()` | `text: str` | `None` | Send text message |
| `receive_json()` | none | `Dict` | Receive and parse JSON |
| `receive_text()` | none | `str` | Receive text |
| `close()` | `code: int = 1000` | `None` | Close connection |
| `on_message()` | `message_type: str` | `Callable` | Register message handler |
| `handle_messages()` | none | `None` | Main message loop |
| `save_state()` | none | `str` | Serialize state to JSON |
| `restore_state()` | `state_json: str` | `None` | Load state from JSON |
| `broadcast_message()` | `message: str, exclude_self: bool = False` | `None` | Broadcast to room |

### ConnectionState

```python
@dataclass
class ConnectionState:
    user_id: str              # User ID
    room: str                 # Room name
    connected_at: str         # ISO timestamp
    metadata: Dict[str, Any]  # Custom data

    def to_json() -> str          # Serialize
    @classmethod
    def from_json(data: str) -> ConnectionState  # Deserialize
```

### ConnectionManager

| Method | Purpose |
|--------|---------|
| `add_connection(websocket, room)` | Register connection in room |
| `remove_connection(websocket)` | Unregister connection |
| `broadcast_to_room(room, message, exclude_user)` | Send to all in room |
| `get_room_info(room)` | Get room statistics |
| `rooms` | Dict of all active rooms |

---

## Complete Example: Real-Time Chat

See the `examples/chat-websocket-auth/` directory in the Eden repository for a complete, production-ready chat application with:
- Token-based authentication
- Multiple rooms
- User presence indicators
- Message persistence
- Reconnection recovery

---

## Troubleshooting

### "No authentication token provided"
- Ensure token is in query string: `ws://...?token=YOUR_TOKEN`
- Check token parameter name matches `token_name` argument

### "WebSocket connection lost on reconnect"  
- State may have expired (check `connected_at`)
- Verify state JSON wasn't corrupted
- Check network connectivity

### "Connection reset after few messages"
- May be hitting rate limits - add delays between sends
- Check server logs for exceptions
- Verify heartbeat task is running

---

## Next Steps

- [Basic WebSocket Guide](websockets.md) - Learn the basics first
- [Security Best Practices](security.md#websocket-authentication) - Authentication patterns
- [Real-Time ORM Sync](websockets.md#reactive-orm-automating-the-ui) - Reactive models
- [Production Examples](../getting-started/learning-path.md) - Sample code flows

