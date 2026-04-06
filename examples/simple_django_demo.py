"""
Simple example showing Django-inspired features in Eden.
Run with: python examples/simple_django_demo.py
"""

from eden import Eden, Model, StringField, TextField
from eden.panel import ControlPanel, BasePanel
from eden.schemas import ModelSchema
from eden.querysets import Manager
from eden.enums import ChoiceField, ChoiceEnum

app = Eden(title="Simple Django Demo", debug=True)

# ────────────────────────────────────────────────────────────────────────
# ChoiceField Example
# ────────────────────────────────────────────────────────────────────────

class Priority(ChoiceEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    @property
    def display_name(self):
        return self.value.title()

# ────────────────────────────────────────────────────────────────────────
# Model with ModelConfig
# ────────────────────────────────────────────────────────────────────────

class Task(Model):
    """A simple task model."""
    title = StringField(max_length=200)
    description = TextField(default="")
    priority = ChoiceField(choices=Priority, default=Priority.MEDIUM)
    completed = StringField(max_length=5, default="false")

    # Custom manager
    objects = TaskManager()

    class Meta:
        verbose_name = "Task"
        api_resource = True
        admin_list_display = ["title", "priority", "completed"]
        admin_list_filter = ["priority", "completed"]
        admin_search_fields = ["title", "description"]

# ────────────────────────────────────────────────────────────────────────
# Custom Manager
# ────────────────────────────────────────────────────────────────────────

class TaskManager(Manager):
    """Custom manager for tasks."""

    def completed(self):
        return self.filter(completed="true")

    def pending(self):
        return self.filter(completed="false")

    def high_priority(self):
        return self.filter(priority=Priority.HIGH.value)

# ────────────────────────────────────────────────────────────────────────
# ModelSchema
# ────────────────────────────────────────────────────────────────────────

class TaskSchema(ModelSchema):
    """Schema for task validation."""

    async def clean_title(self, value):
        if len(value.strip()) < 3:
            from eden.schemas import ValidationError
            raise ValidationError("Title must be at least 3 characters")
        return value.strip()

    class Meta:
        model = Task
        required_fields = ["title"]

# ────────────────────────────────────────────────────────────────────────
# Admin Panel
# ────────────────────────────────────────────────────────────────────────

class TaskPanel(BasePanel):
    """Admin panel for tasks."""
    display_fields = ["title", "priority", "completed"]
    search_fields = ["title", "description"]
    filter_fields = ["priority", "completed"]

# ────────────────────────────────────────────────────────────────────────
# Setup Admin
# ────────────────────────────────────────────────────────────────────────

panel = ControlPanel()
panel.register(Task)(TaskPanel)

# ────────────────────────────────────────────────────────────────────────
# Routes
# ────────────────────────────────────────────────────────────────────────

@app.get("/")
async def home():
    """Home page."""
    return {
        "message": "Simple Django Features Demo",
        "endpoints": {
            "admin": "/admin",
            "api_tasks": "/api/tasks",
            "create_task": "POST /api/tasks"
        }
    }

@app.get("/api/tasks")
async def list_tasks(status: str = None):
    """List tasks."""
    if status == "completed":
        tasks = await Task.objects.completed().all()
    elif status == "pending":
        tasks = await Task.objects.pending().all()
    else:
        tasks = await Task.objects.all()

    return {"tasks": tasks, "count": len(tasks)}

@app.post("/api/tasks")
async def create_task(request):
    """Create a task."""
    data = await request.json()
    schema = TaskSchema(**data)

    if await schema.is_valid(data):
        task = await schema.save()
        return {"task": task, "message": "Task created!"}
    else:
        return {"errors": schema.errors}

@app.put("/api/tasks/{task_id}/complete")
async def complete_task(task_id: str):
    """Mark task as completed."""
    task = await Task.objects.filter(id=task_id).first()
    if task:
        task.completed = "true"
        await task.save()
        return {"task": task, "message": "Task completed!"}
    return {"error": "Task not found"}

# Admin routes
@app.route("/admin/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def admin_handler(request):
    return await panel.handle_request(request)

if __name__ == "__main__":
    print("🚀 Simple Django Features Demo")
    print("📋 Features:")
    print("  • ChoiceField enums")
    print("  • ModelConfig metadata")
    print("  • Custom QuerySet managers")
    print("  • ModelSchema validation")
    print("  • ControlPanel admin interface")
    print("\n🌐 Visit http://localhost:8000")
    print("🔧 Admin interface at http://localhost:8000/admin")

    app.run(host="0.0.0.0", port=8000)