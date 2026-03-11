# Quick Start 🚀

In this guide, we'll build a minimal Eden application that demonstrates routing and database connectivity.

## 1. Create your App

Create a file named `app.py`:

```python
from eden import Eden
from eden.db import Database

# Initialize Database (SQLite)
db = Database("sqlite+aiosqlite:///db.sqlite3")

# Initialize Eden App
app = Eden(
    title="Genesis", 
    debug=True,
    description="My first Eden project"
)
app.db = db

# Define a Route
@app.get("/")
async def welcome(request):
    return {"message": "Welcome to Eden! 🌿"}

# Connect to Database on Startup
@app.on_startup
async def startup():
    await db.connect(create_tables=True)

if __name__ == "__main__":
    app.run(port=8888)
```

## 2. Run the Application

Execute your script:

```bash
python app.py
```

You should see output indicating that the server is running. Open your browser to `http://localhost:8888`.

## 3. Using the CLI

If you used `eden new`, you can also use the `eden` command-line tool:

```bash
# Run the development server
eden run

# Check the framework version
eden version
```

## 4. Your First Template

Eden really shines when you start using its template engine. Let's render an HTML page.

### Create `templates/hello.html`

```html
<!DOCTYPE html>
<html>
<head>
    <title>Hello Eden</title>
</head>
<body class="bg-slate-900 text-white p-8">
    <h1 class="text-4xl font-bold">Hello, {{ name }}!</h1>
    <p class="mt-4">You are running on Eden Framework.</p>
</body>
</html>
```

### Update `app.py`

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
