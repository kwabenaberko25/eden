# Example Snippets — Quick Reference

Quick code snippets from all 7 examples for copy-paste reference. Explore the [Full Examples](learning-path.md) for more complex patterns.

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

## 10. Multi-Tenancy (SaaS)

```python
from eden import TenantMixin

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
