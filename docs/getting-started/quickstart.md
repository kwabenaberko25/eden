# Quick Start 🚀

Build your first Eden application in 10 minutes with routing, database models, and forms.

## Step 1: Initialize Your App

Create `app.py`:

```python
from eden import Eden, Model, StringField, BoolField, Request
from datetime import datetime

app = Eden(
    title="My First Eden App",
    secret_key="dev-secret-key-change-in-prod",
    debug=True
)

# Configure database
app.state.database_url = "sqlite+aiosqlite:///app.db"

# Add middleware for security and sessions
app.add_middleware("security")
app.add_middleware("session", secret_key=app.secret_key)
app.add_middleware("csrf")
app.add_middleware("gzip")

# Root endpoint
@app.get("/")
async def home():
    return {"message": "Welcome to Eden! 🌿"}

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)
```

**Run it**:
```bash
python app.py
# Visit http://localhost:8000
```

---

## Step 2: Add a Database Model

Add this to your `app.py`:

```python
from eden import Eden, Model, StringField, TextField, BoolField, Request
from sqlalchemy.orm import Mapped

# Define a Task model
class Task(Model):
    """A simple todo task."""
    title: Mapped[str] = StringField(max_length=200)
    description: Mapped[str | None] = TextField(nullable=True)
    completed: Mapped[bool] = BoolField(default=False)

# List all tasks
@app.get("/tasks")
async def list_tasks():
    tasks = await Task.all()
    return {
        "count": len(tasks),
        "tasks": [t.to_dict() for t in tasks]
    }

# Create a new task
@app.post("/tasks")
async def create_task(request: Request):
    data = await request.json()
    task = await Task.create(
        title=data.get("title", "Untitled"),
        description=data.get("description", "")
    )
    return {"id": task.id, "title": task.title}, 201

# Get single task
@app.get("/tasks/{task_id:int}")
async def get_task(task_id: int):
    task = await Task.get(task_id)
    if not task:
        return {"error": "Task not found"}, 404
    return task.to_dict()

# Update task
@app.put("/tasks/{task_id:int}")
async def update_task(request: Request, task_id: int):
    task = await Task.get(task_id)
    if not task:
        return {"error": "Task not found"}, 404
    
    data = await request.json()
    await task.update(**data)
    return task.to_dict()

# Mark task complete
@app.post("/tasks/{task_id:int}/complete")
async def complete_task(task_id: int):
    task = await Task.get(task_id)
    if not task:
        return {"error": "Task not found"}, 404
    
    task.completed = True
    await task.save()
    return {"completed": True}

# Delete task
@app.delete("/tasks/{task_id:int}")
async def delete_task(task_id: int):
    task = await Task.get(task_id)
    if not task:
        return {"error": "Task not found"}, 404
    
    await task.delete()
    return {"deleted": True}
```

**Test with curl**:
```bash
# Create task
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"Learn Eden","description":"Master the framework"}'

# List tasks
curl http://localhost:8000/tasks

# Get single task
curl http://localhost:8000/tasks/1

# Complete task
curl -X POST http://localhost:8000/tasks/1/complete

# Delete task
curl -X DELETE http://localhost:8000/tasks/1
```

---

## Step 3: Create HTML Templates

Create `templates/base.html`:

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>@span(title | default("My App"))</title>
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50">
    <nav class="bg-white shadow">
        <div class="max-w-6xl mx-auto px-4 py-4">
            <h1 class="text-2xl font-bold text-blue-600">🌿 Eden</h1>
        </div>
    </nav>
    
    <main class="max-w-6xl mx-auto px-4 py-8">
        @yield("content")
    </main>
</body>
</html>
```

Create `templates/tasks.html`:

```html
@extends("base")

@section("content") {
    <h2 class="text-3xl font-bold mb-6">My Tasks</h2>
    
    <!-- Task Form -->
    <div class="bg-white p-6 rounded-lg shadow mb-6">
        <h3 class="text-xl font-bold mb-4">Add New Task</h3>
        <form method="POST" action="/tasks/create" class="space-y-4">
            @csrf
            
            <div>
                <label class="block text-sm font-medium mb-1">Title</label>
                <input type="text" name="title" class="w-full px-4 py-2 border rounded-lg" required>
            </div>
            
            <div>
                <label class="block text-sm font-medium mb-1">Description</label>
                <textarea name="description" rows="4" class="w-full px-4 py-2 border rounded-lg"></textarea>
            </div>
            
            <button type="submit" class="bg-blue-600 text-white px-4 py-2 rounded-lg font-medium">
                Add Task
            </button>
        </form>
    </div>
    
    <!-- Task List -->
    <div class="grid gap-4">
        @if (tasks | length > 0) {
            @for (task in tasks) {
                <div class="bg-white p-4 rounded-lg shadow flex items-start justify-between">
                    <div class="flex-1">
                        <h4 class="font-bold text-lg @if(task.completed) line-through text-gray-400 @endif">
                            @span(task.title)
                        </h4>
                        @if (task.description) {
                            <p class="text-gray-600 mt-2">@span(task.description)</p>
                        }
                    </div>
                    
                    <div class="flex gap-2 ml-4">
                        @if (!task.completed) {
                            <form method="POST" action="/tasks/@span(task.id)/complete" style="display:inline;">
                                @csrf
                                <button type="submit" class="bg-green-500 text-white px-3 py-1 rounded text-sm">
                                    ✓ Complete
                                </button>
                            </form>
                        }
                        
                        <form method="POST" action="/tasks/@span(task.id)/delete" style="display:inline;">
                            @csrf
                            <button type="submit" class="bg-red-500 text-white px-3 py-1 rounded text-sm" 
                                    onclick="return confirm('Delete this task?')">
                                Delete
                            </button>
                        </form>
                    </div>
                </div>
            }
        } @else {
            <div class="bg-white p-8 rounded-lg text-center text-gray-500">
                <p>No tasks yet. Create one to get started!</p>
            </div>
        }
    </div>
}
```

---

## Step 4: Connect Templates to Routes

Update your `app.py` to render HTML:

```python
from eden import render_template

# Render task list
@app.get("/tasks/view")
async def view_tasks():
    tasks = await Task.all()
    return render_template("tasks.html", {"tasks": tasks})

# Create task from form
@app.post("/tasks/create")
async def create_task_form(request: Request):
    form = await request.form()
    task = await Task.create(
        title=form.get("title"),
        description=form.get("description", "")
    )
    return request.app.redirect("/tasks/view")

# Delete task from form
@app.post("/tasks/{task_id:int}/delete")
async def delete_task_form(task_id: int):
    task = await Task.get(task_id)
    if task:
        await task.delete()
    return app.redirect("/tasks/view")
```

**Visit**: `http://localhost:8000/tasks/view`

---

## Step 5: Add Users & Authentication

For a todo app with user accounts, add:

```python
from eden.auth import hash_password, verify_password

class User(Model):
    """User for authentication."""
    email: Mapped[str] = StringField(max_length=255, unique=True)
    password: Mapped[str] = StringField()
    name: Mapped[str] = StringField(max_length=255)
    is_active: Mapped[bool] = BoolField(default=True)

# Update Task to belong to User
class Task(Model):
    """Task belongs to a user."""
    title: Mapped[str] = StringField(max_length=200)
    description: Mapped[str | None] = TextField(nullable=True)
    completed: Mapped[bool] = BoolField(default=False)
    user_id: Mapped[int] = IntegerField()  # Foreign key to User

# Register route
@app.post("/register")
async def register(request: Request):
    data = await request.json()
    user = await User.create(
        email=data["email"],
        password=data["password"],  # Auto-hashed by Eden
        name=data.get("name", "User")
    )
    return {"id": user.id, "email": user.email}

# Login route
@app.post("/login")
async def login(request: Request):
    data = await request.json()
    user = await User.filter(email=data["email"]).first()
    
    if not user or not verify_password(data["password"], user.password):
        return {"error": "Invalid credentials"}, 401
    
    request.session["user_id"] = str(user.id)
    return {"message": "Logged in successfully"}

# Protected route
@app.get("/my-tasks")
async def my_tasks(request: Request):
    if "user_id" not in request.session:
        return {"error": "Not authenticated"}, 401
    
    user_id = int(request.session["user_id"])
    tasks = await Task.filter(user_id=user_id).all()
    return {"tasks": [t.to_dict() for t in tasks]}
```

---

## What's Next?

1. **Run this code**: `python app.py`
2. **Test the API**: Use curl or Postman
3. **Explore examples**: Check [Learning Path](learning-path.md)
4. **Read full guides**: See [Routing](../guides/routing.md) and [ORM](../guides/orm.md)
5. **Follow tutorials**: Step through [Task 1](../tutorial/task1_setup.md)

**Congratulations! You've built a fully functional task management app. 🎉**

```python
@app.get("/hello/{name}")
async def hello(request, name: str):
    return request.render("hello.html", {"name": name})

---

## 5. Your First Model

Eden makes data management effortless. Let's add a `Task` model to our `app.py`.

```python
from sqlalchemy.orm import Mapped
from eden.db import EdenModel, StringField, BoolField

class Task(EdenModel):
    title: Mapped[str] = StringField(max_length=200)
    completed: Mapped[bool] = BoolField(default=False)

# Add a route to create and list tasks
@app.route("/tasks", methods=["GET", "POST"])
async def tasks(request):
    if request.method == "POST":
        form_data = await request.form()
        await Task.create(title=form_data["title"])
    
    all_tasks = await Task.all()
    return request.render("tasks.html", {"tasks": all_tasks})
```

---

## What's Next?

You've just built a secure, async-powered application with a custom template and database model.

- Explore the **[Project Structure](structure.md)** to see how to scale this app.
- Dive into the **[ORM Guide](../guides/orm.md)** to master data relationships.
- Learn about **[Authentication](../guides/auth.md)** to protect your routes.

```markdown

---

**Next Steps**: [Project Structure](structure.md)
