# Example Snippets — Quick Reference

Quick code snippets from all 7 examples for copy-paste reference.

## 1. Hello World — Minimal App

```python
from eden import Eden

app = Eden(title="My App", debug=True)

@app.get("/")
async def hello():
    return {"message": "Hello!"}

if __name__ == "__main__":
    app.run()
```

**Run**: `eden run` → Visit `http://localhost:8000`

---

## 2. Models and ORM

```python
from eden import Model, StringField, IntField, BoolField

class Task(Model):
    title = StringField(max_length=200)
    description = StringField(blank=True)
    priority = IntField(default=1)
    completed = BoolField(default=False)

# Create
task = await Task.create(title="Learn Eden", priority=1)

# Read all
tasks = await Task.all()

# Filter
completed = await Task.filter(completed=True).all()

# Get single
task = await Task.get(1)

# Update
task.completed = True
await task.save()

# Delete
await task.delete()
```

---

## 3. REST API Endpoints

```python
from eden import Request

# GET - List all
@app.get("/tasks")
async def list_tasks():
    return {"tasks": await Task.all()}

# GET - Single item
@app.get("/tasks/{task_id:int}")
async def get_task(task_id: int):
    return await Task.get(task_id)

# POST - Create
@app.post("/tasks")
async def create_task(request: Request):
    data = await request.json()
    task = await Task.create(**data)
    return task

# PUT - Update
@app.put("/tasks/{task_id:int}")
async def update_task(task_id: int, request: Request):
    task = await Task.get(task_id)
    data = await request.json()
    for key, value in data.items():
        setattr(task, key, value)
    await task.save()
    return task

# DELETE - Remove
@app.delete("/tasks/{task_id:int}")
async def delete_task(task_id: int):
    await Task.delete(task_id)
    return {"deleted": True}
```

---

## 4. Routing and Path Parameters

```python
# Simple path parameter
@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return {"user_id": user_id}

# Multiple parameters
@app.get("/posts/{post_id}/comments/{comment_id}")
async def get_comment(post_id: int, comment_id: int):
    return {"post_id": post_id, "comment_id": comment_id}

# Query parameters
@app.get("/search")
async def search(q: str, skip: int = 0, limit: int = 10):
    return {"query": q, "skip": skip, "limit": limit}

# Accept JSON body
@app.post("/items")
async def create_item(request: Request):
    data = await request.json()
    return {"created": True, "data": data}

# Accept form data
@app.post("/upload")
async def upload(request: Request):
    form = await request.form()
    file = form.get("file")
    return {"uploaded": True}
```

---

## 5. Authentication & Sessions

```python
from eden import login_required

# Initialize session middleware
app.add_middleware("session", secret_key=app.secret_key)

# Login endpoint
@app.post("/login")
async def login(request: Request):
    form = await request.form()
    username = form.get("username")
    password = form.get("password")
    
    # Verify credentials
    user = await User.filter(username=username).first()
    if user and user.verify_password(password):
        request.session["user_id"] = user.id
        return {"success": True}
    return {"success": False}

# Protected endpoint
@app.get("/profile")
@login_required
async def profile(request: Request):
    user_id = request.session.get("user_id")
    user = await User.get(user_id)
    return user

# Logout
@app.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return {"success": True}
```

---

## 6. Templates & HTML Rendering

```python
from eden import render_template

@app.get("/")
async def index():
    tasks = await Task.all()
    return render_template("tasks.html", {"tasks": tasks})

@app.post("/tasks")
async def create_task(request: Request):
    form = await request.form()
    task = await Task.create(title=form.get("title"))
    return render_template("task_item.html", {"task": task})
```

**Template** (`templates/tasks.html`):
```html
<!DOCTYPE html>
<html>
<head><title>Tasks</title></head>
<body>
    <h1>Tasks</h1>
    <ul>
    @for (task in tasks) {
        <li>@span(task.title) @if (task.completed) { <s>(Done)</s> }</li>
    }
    </ul>
</body>
</html>
```

---

## 7. Relationships (Foreign Keys)

```python
from eden import ForeignKeyField

class User(Model):
    name = StringField()

class Post(Model):
    title = StringField()
    author_id = ForeignKeyField(User)  # Foreign key

# Create with relationship
user = await User.create(name="Alice")
post = await Post.create(title="Hello", author_id=user.id)

# Query with eager loading
posts = await Post.select().prefetch_related("author").all()
for post in posts:
    print(f"{post.title} by {post.author.name}")
```

---

## 8. Filtering and Complex Queries

```python
from eden import Q, F

# Simple filter
completed = await Task.filter(completed=True).all()

# Multiple filters (AND)
tasks = await Task.filter(completed=False, priority=1).all()

# OR queries
urgent = await Task.filter(
    Q(priority=1) | Q(completed=False)
).all()

# Field comparisons
reviews = await Product.filter(rating__gte=4).all()  # rating >= 4

# Ordering
tasks = await Task.select().order_by("-priority").all()

# Limit and offset
tasks = await Task.select().limit(10).offset(20).all()

# Count
total = await Task.count()
```

---

## 9. Middleware

```python
# Built-in middleware
app.add_middleware("security")      # Security headers
app.add_middleware("cors", allow_origins=["*"])
app.add_middleware("session", secret_key=app.secret_key)
app.add_middleware("csrf")          # CSRF protection
app.add_middleware("gzip")          # Compression

# Or use setup_defaults() for common middleware
app.setup_defaults()

# Custom middleware
@app.middleware("http")
async def custom_middleware(request, call_next):
    request.state.start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - request.state.start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
```

---

## 9. Middleware

```python
# Built-in middleware
app.add_middleware("security")      # Security headers
app.add_middleware("cors", allow_origins=["*"])
app.add_middleware("session", secret_key=app.secret_key)
app.add_middleware("csrf")          # CSRF protection
app.add_middleware("gzip")          # Compression

# Or use setup_defaults() for common middleware
app.setup_defaults()

# Custom middleware
@app.middleware("http")
async def custom_middleware(request, call_next):
    request.state.start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - request.state.start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
```

---

## 10. Error Handling

```python
from eden import Exception, NotFound, Unauthorized, Forbidden

# Catch specific exceptions
@app.get("/items/{item_id}")
async def get_item(item_id: int):
    item = await Item.get(item_id)
    if not item:
        raise NotFound("Item not found")
    return item

# Global error handler
@app.exception_handler(Exception)
async def exception_handler(request, exc):
    return {
        "error": str(exc),
        "status": "error"
    }, 500

# Permission checks
@app.delete("/posts/{post_id}")
async def delete_post(request: Request, post_id: int):
    post = await Post.get(post_id)
    
    if post.author_id != request.user.id and not request.user.is_admin:
        raise Forbidden("You can only delete your own posts")
    
    await post.delete()
    return {"deleted": True}
```

---

## 11. Background Tasks & Async Operations

```python
from eden.tasks import background_task
from datetime import datetime, timedelta

# Queue a background task
@app.post("/send-email")
async def send_email_later(request: Request):
    email = await request.json()
    
    # Queue task (runs in background)
    await background_task(
        send_email_async,
        email=email["to"],
        subject="Welcome!",
        delay=5  # Run after 5 seconds
    )
    
    return {"queued": True}

async def send_email_async(email: str, subject: str):
    """This runs asynchronously."""
    await send_mail(to=email, subject=subject, template="welcome.html")
```

---

## 12. Pagination

```python
from eden.pagination import Paginator

@app.get("/posts")
async def list_posts(page: int = 1, per_page: int = 20):
    # Offset-based pagination
    posts = await Post.select() \
        .limit(per_page) \
        .offset((page - 1) * per_page) \
        .all()
    
    total = await Post.count()
    
    return {
        "posts": [p.to_dict() for p in posts],
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": (total + per_page - 1) // per_page
    }

# Cursor-based pagination (better for large datasets)
@app.get("/posts/cursor")
async def list_posts_cursor(cursor: str = None, limit: int = 20):
    query = Post.select()
    
    if cursor:
        # cursor is a base64-encoded ID
        import base64
        last_id = int(base64.b64decode(cursor))
        query = query.where(Post.id > last_id)
    
    posts = await query.limit(limit + 1).all()
    
    has_more = len(posts) > limit
    posts = posts[:limit]
    
    next_cursor = None
    if has_more and posts:
        import base64
        next_cursor = base64.b64encode(str(posts[-1].id).encode()).decode()
    
    return {
        "posts": [p.to_dict() for p in posts],
        "next_cursor": next_cursor,
        "has_more": has_more
    }
```

---

## 13. Validation & Schemas

```python
from eden.forms import Schema, EmailStr, field
from pydantic import field_validator

class UserRegistration(Schema):
    name: str = field(min_length=2, max_length=100, label="Full Name")
    email: EmailStr = field(label="Email Address")
    password: str = field(min_length=8, label="Password")
    password_confirm: str = field(label="Confirm Password")
    
    @field_validator('password_confirm')
    def passwords_match(cls, v, info):
        if v != info.data.get('password'):
            raise ValueError('Passwords do not match')
        return v

# Use in route with automatic validation
@app.post("/register")
@app.validate(UserRegistration, template="register.html")
async def register(request: Request, data: UserRegistration):
    # This only runs if validation passes!
    user = await User.create(
        name=data.name,
        email=data.email,
        password=data.password  # Auto-hashed
    )
    return {"success": True, "user": user.to_dict()}
```

---

## 14. Transactions & Atomicity

```python
from eden.db import transaction

async def transfer_funds(from_user_id: int, to_user_id: int, amount: float):
    """Transfer funds atomically - either both succeed or both fail."""
    
    async with transaction():
        # Get users with row-level lock
        from_user = await User.get(from_user_id)
        to_user = await User.get(to_user_id)
        
        if from_user.balance < amount:
            raise ValueError("Insufficient funds")
        
        # Deduct from sender
        from_user.balance -= amount
        await from_user.save()
        
        # Add to recipient
        to_user.balance += amount
        await to_user.save()
        
        # Record transaction
        await Transaction.create(
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            amount=amount
        )

# Use in route
@app.post("/transfer")
async def handle_transfer(request: Request):
    data = await request.json()
    try:
        await transfer_funds(
            from_user_id=request.user.id,
            to_user_id=data["to_id"],
            amount=data["amount"]
        )
        return {"success": True}
    except ValueError as e:
        return {"error": str(e)}, 400
```

---

## 15. File Uploads & Storage

```python
from eden.storage import storage

@app.post("/upload-avatar")
async def upload_avatar(request: Request):
    """Handle file upload to storage (S3 or local)."""
    form = await request.form()
    file = form.get("avatar")
    
    if not file:
        return {"error": "No file provided"}, 400
    
    # Save to storage
    path = f"avatars/{request.user.id}/{file.filename}"
    saved_path = await storage.save(path, file)
    
    # Get public URL
    url = await storage.url(saved_path)
    
    # Update user
    request.user.avatar_url = url
    await request.user.save()
    
    return {"url": url}
```

---

## 16. Real-Time Updates with WebSockets

```python
from eden.websocket import WebSocketRoute

@app.websocket("/ws/chat/{room_id}")
async def websocket_chat(websocket, room_id: str):
    """Handle WebSocket connections for real-time chat."""
    await websocket.accept()
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            
            # Broadcast to room
            await broadcast_to_room(room_id, {
                "user": websocket.user.name,
                "message": data["message"],
                "timestamp": datetime.now().isoformat()
            })
    except Exception as e:
        await websocket.close(code=1000)

async def broadcast_to_room(room_id: str, message: dict):
    """Broadcast message to all connected clients in a room."""
    # Implementation depends on your connection management
    pass
```

---

## 17. Testing Patterns

```python
import pytest
from httpx import AsyncClient
from app import app, create_app

@pytest.fixture
async def client():
    """Create test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_create_post(client):
    """Test creating a post."""
    response = await client.post("/posts", json={
        "title": "Test Post",
        "content": "Test content"
    })
    assert response.status_code == 201
    assert response.json()["title"] == "Test Post"

@pytest.mark.asyncio
async def test_post_not_found(client):
    """Test 404 handling."""
    response = await client.get("/posts/999999")
    assert response.status_code == 404
```

---

## 18. Logging & Monitoring

```python
import logging
from eden.telemetry import record_metric

logger = logging.getLogger(__name__)

@app.middleware("http")
async def log_requests(request, call_next):
    """Log all requests."""
    logger.info(f"{request.method} {request.url.path}")
    
    response = await call_next(request)
    
    # Record metric
    record_metric("http_requests", 1, tags={
        "method": request.method,
        "status": response.status_code
    })
    
    return response

# Configure logging
from eden.logging import setup_logging

setup_logging(
    level="INFO",
    format="json"  # Structured logging for production
)
```

---

## 19. Rate Limiting

```python
# Built-in rate limiting middleware
app.add_middleware(
    "ratelimit",
    max_requests=100,
    window_seconds=60,
    key_func=lambda request: request.client.host  # Per IP
)

# Custom rate limiting per user
from functools import wraps

async def rate_limit_user(max_requests=100, window=60):
    """Decorator for per-user rate limiting."""
    @wraps
    async def decorator(func):
        async def wrapper(request, *args, **kwargs):
            user_id = request.user.id if request.user else None
            key = f"ratelimit:{user_id}"
            
            # Check cache for request count
            count = await cache.get(key) or 0
            if count >= max_requests:
                return {"error": "Rate limit exceeded"}, 429
            
            await cache.set(key, count + 1, window)
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator
```

---

**See full documentation in the [Guides](../guides/) section for in-depth examples and best practices.**

app.add_middleware("tenant")

class Organization(Model):
    name = StringField()

class Document(Model, TenantMixin):
    title = StringField()
    organization_id = ForeignKeyField(Organization)

# Automatically filtered by tenant
@app.get("/documents")
async def list_docs(request):
    # request.tenant.id is set by middleware
    docs = await Document.filter(
        organization_id=request.tenant.id
    ).all()
    return {"documents": docs}
```

---

## 11. Background Jobs & Tasks

```python
from eden import app

@app.task()
async def send_email(email: str, subject: str):
    """Background task."""
    # This runs in a worker process
    await mail.send(email, subject)
    return {"sent": True}

# Queue a task
@app.post("/contact")
async def contact(request: Request):
    data = await request.json()
    # This returns immediately, runs in background
    send_email.delay(data["email"], "Thanks for contacting us")
    return {"message": "Email queued"}
```

---

## 12. Configuration & Environment

```python
import os
from dotenv import load_dotenv

load_dotenv()  # Load from .env file

DEBUG = os.getenv("DEBUG", "false").lower() == "true"
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///db.sqlite3")
SECRET_KEY = os.getenv("SECRET_KEY", "change-me")

app = Eden(
    title="My App",
    debug=DEBUG,
    secret_key=SECRET_KEY
)
app.state.database_url = DATABASE_URL
```

---

## Quick Syntax Reference

| Operation | Syntax |
|-----------|--------|
| Create app | `app = Eden(title="...", debug=True)` |
| GET route | `@app.get("/path")` |
| POST route | `@app.post("/path")` |
| Path param | `@app.get("/users/{user_id}")` |
| Create model | `class User(Model): name = StringField()` |
| Create record | `user = await User.create(name="Alice")` |
| Query all | `users = await User.all()` |
| Filter | `users = await User.filter(active=True).all()` |
| Get one | `user = await User.get(1)` |
| Update | `user.name = "Bob"; await user.save()` |
| Delete | `await user.delete()` |
| Template | `render_template("file.html", data)` |
| Session | `request.session["key"] = value` |
| Middleware | `app.add_middleware("name", option=value)` |
| Protect route | `@login_required` |
| Run server | `app.run()` or `eden run` |

---

**See full examples**: [Learning Path](learning-path.md) | [Examples Directory](../../examples/)
