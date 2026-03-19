# Premium Code Gallery 💎

**Copy-pasteable, production-ready patterns for every layer of your Eden application. These snippets represent the "Eden Way"—writing less code to achieve more impact.**

---

## 💾 Layer 1: High-Performance Data Models

Eden's ORM is designed for SaaS-scale data. Use these patterns to define robust schemas with automatic audit trails.

### The "SaaS Unit" Pattern

A model with multi-tenancy support and precise decimal handling for financial apps.

```python
from eden import Model, f
from sqlalchemy.orm import Mapped
from decimal import Decimal

class Product(Model):
    """
    Automatic multi-tenancy: Inherit from TenantModel for automatic isolation.
    """
    name: Mapped[str] = f(max_length=100, index=True)
    price: Mapped[Decimal] = f(precision=10, scale=2)
    stock: Mapped[int] = f(default=0)
    
    # Audit trail is enabled by default in Eden models
    # access task.created_at, task.updated_at, task.version
```

### Complex Relationships

Defining a clean One-to-Many relationship with cascading deletes.

```python
from eden import Model, f, ForeignKeyField
from sqlalchemy.orm import Mapped, relationship

class Category(Model):
    name: Mapped[str] = f()
    products: Mapped[list["Product"]] = relationship(back_populates="category")

class Product(Model):
    name: Mapped[str] = f()
    category_id: Mapped[int] = ForeignKeyField("category.id", ondelete="CASCADE")
    category: Mapped["Category"] = relationship(back_populates="products")
```

> [!TIP]
> **Success Pattern**: Use `index=True` on fields you'll query frequently. Eden automatically translates this to high-performance SQL indices.

---

## ⚡ Layer 2: Reactive UI Patterns (HTMX)

Eliminate complex JavaScript by using Eden's Server-Side Fragments.

### The "Inline Edit" Pattern

Allow users to edit data without a page reload.

```python
@app.get("/task/{id}/edit")
async def edit_task(id: int):
    task = await Task.get(id)
    return render_template("tasks.html", {"task": task}, fragment="edit-form")

@app.post("/task/{id}/save")
async def save_task(request: Request, id: int):
    task = await Task.get(id)
    form = await request.form()
    await task.update(title=form.get("title"))
    return render_template("tasks.html", {"task": task}, fragment="task-row")
```

### Real-Time Search

A zero-JS search bar that updates as the user types.

```html
<input type="text" 
       name="search" 
       placeholder="Search products..." 
       hx-post="/search" 
       hx-trigger="keyup changed delay:500ms" 
       hx-target="#search-results"
       class="w-full p-4 rounded-xl border-slate-200">

<div id="search-results">
    <!-- Results go here -->
</div>
```

---

## 🔒 Layer 3: Advanced Security & Auth

Eden makes hard security problems simple with built-in decorators.

### Role-Based Access Control (RBAC)

Protecting routes with fine-grained permissions.

```python
from eden.auth import login_required, permissions_required

@app.get("/admin/reports")
@login_required
@permissions_required("view_analytics", "export_data")
async def get_reports():
    return {"data": "Top Secret 🤫"}
```

### Manual Session Management

For when you need custom control over the user's session.

```python
@app.post("/login")
async def login(request: Request):
    user = await authenticate(request)
    if user:
        # Secure, encrypted cookie-based sessions
        request.session["user_id"] = str(user.id)
        request.session["last_login"] = user.updated_at.isoformat()
        return request.app.redirect("/dashboard")
```

---

## ⚙️ Layer 4: Background Automation

Don't block the main thread. Eden integrates with Taskiq for industrial-grade task queuing.

### The "Fire and Forget" Task

Perfect for sending emails or processing images.

```python
from eden.tasks import task

@task()
async def send_welcome_email(user_id: int):
    user = await User.get(user_id)
    # Email logic here...
    print(f"Sent email to {user.email}")

@app.post("/signup")
async def signup(request: Request):
    user = await User.create(...)
    # Execution happens on a worker process
    await send_welcome_email.kiq(user.id)
    return {"status": "User created. Email queued."}
```

---

## 🏗️ Layer 5: App-Level Configuration

Control your entire Eden ecosystem from one central definition.

### The "SaaS Engine" Config

The recommended setup for modern application stacks.

```python
app = Eden(
    title="Eden Pro",
    secret_key=os.environ["SECRET_KEY"],
    
    # Automatic caching & rate limiting
    redis_url="redis://localhost:6379/0",
    
    # Global exception handling customization
    exception_handlers={
        404: lambda req, exc: render_template("404.html"),
        500: lambda req, exc: render_template("500.md")
    }
)
```

---

### 🎨 Design Token Cheat Sheet

When styling your templates with Tailwind (included in Eden by default), use these "Premium" color scales for a refined look:

* **Primary Action**: `bg-blue-600 hover:bg-blue-700 text-white`
* **Surface / Cards**: `bg-white border border-slate-100 shadow-sm rounded-2xl`
* **Secondary Text**: `text-slate-500 font-medium`
* **Success Indicator**: `bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200`

