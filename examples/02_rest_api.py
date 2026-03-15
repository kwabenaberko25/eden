"""
02_rest_api.py — REST API with Models

Add a database and ORM models to build a real REST API.
This example uses SQLite and async/await throughout.

Run:
    python examples/02_rest_api.py

Then try:
    curl -X GET http://localhost:8000/tasks
    curl -X POST http://localhost:8000/tasks -d '{"title":"Buy milk"}'
    curl -X GET http://localhost:8000/tasks/1
"""

from eden import Eden, Model, StringField, BoolField, Request

app = Eden(title="REST API", debug=True, secret_key="demo")

# Configure database
app.state.database_url = "sqlite+aiosqlite:///tasks.db"

# ────────────────────────────────────────────────────────────────────────
# Model Definition
# ────────────────────────────────────────────────────────────────────────

class Task(Model):
    """Simple task model."""
    title = StringField(max_length=200)
    completed = BoolField(default=False)


# ────────────────────────────────────────────────────────────────────────
# API Endpoints
# ────────────────────────────────────────────────────────────────────────

@app.get("/tasks")
async def list_tasks():
    """List all tasks."""
    tasks = await Task.all()
    return {"tasks": [{"id": t.id, "title": t.title, "completed": t.completed} for t in tasks]}


@app.post("/tasks")
async def create_task(request: Request):
    """Create a new task from JSON body."""
    data = await request.json()
    task = await Task.create(title=data.get("title", "Untitled"))
    return {"id": task.id, "title": task.title, "completed": task.completed}


@app.get("/tasks/{task_id:int}")
async def get_task(task_id: int):
    """Get a single task by ID."""
    task = await Task.get(task_id)
    return {"id": task.id, "title": task.title, "completed": task.completed}


@app.put("/tasks/{task_id:int}")
async def update_task(task_id: int, request: Request):
    """Update a task."""
    task = await Task.get(task_id)
    data = await request.json()
    
    if "title" in data:
        task.title = data["title"]
    if "completed" in data:
        task.completed = data["completed"]
    
    await task.save()
    return {"id": task.id, "title": task.title, "completed": task.completed}


@app.delete("/tasks/{task_id:int}")
async def delete_task(task_id: int):
    """Delete a task."""
    await Task.delete(task_id)
    return {"deleted": True}


if __name__ == "__main__":
    app.setup_defaults()
    app.run(port=8000)

# What you learned:
#   - Creating a Model class (inherits from Model)
#   - Field types: StringField, BoolField
#   - Database queries: Task.all(), Task.create(), Task.get()
#   - REST endpoints for CRUD operations
#   - Request body parsing: await request.json()
#   - HTTP methods: GET, POST, PUT, DELETE
#   - URL parameters with type hints: {task_id:int}
#
# Next: See 03_web_app.py to add HTML templates and forms
