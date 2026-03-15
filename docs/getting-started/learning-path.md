# Learning Path 📚

Eden includes 7 progressive examples that guide you from hello-world to production-ready applications. Each example builds on the previous concepts and introduces new features.

## The Seven Examples

### 1️⃣ Hello World — Basic Routing (5 minutes)

**File**: `examples/01_hello.py`

Learn the absolute basics:
- Creating an Eden app instance
- Defining GET and POST routes
- Path parameters and query parameters
- Returning JSON responses

```python
from eden import Eden

app = Eden(title="Hello Eden", debug=True)

@app.get("/")
async def hello():
    """Root endpoint - returns JSON."""
    return {"message": "Hello, Eden! 🌿"}

@app.get("/greet/{name}")
async def greet(name: str):
    """Greet a person by name (path parameter)."""
    return {"greeting": f"Hello, {name}!"}

@app.get("/items")
async def list_items(skip: int = 0, limit: int = 10):
    """Query parameters example."""
    return {
        "skip": skip,
        "limit": limit,
        "items": [f"Item {i}" for i in range(skip, skip + limit)]
    }

if __name__ == "__main__":
    app.run(port=8000)
```

**Run it**:
```bash
eden run examples/01_hello.py
# Visit http://localhost:8000
# Try: http://localhost:8000/greet/Alice
# Try: http://localhost:8000/items?skip=5&limit=3
```

**Output**:
```json
{"message": "Hello, Eden! 🌿"}
```

**Concepts**: Decorators, routing, HTTP methods, async functions, path/query parameters

**When to use**: Starting completely fresh, understanding framework fundamentals

---

### 2️⃣ REST API — Database CRUD (15 minutes)

**File**: `examples/02_rest_api.py`

Building a complete RESTful API:
- Setting up SQLite database
- Defining database models
- CRUD operations (Create, Read, Update, Delete)
- Proper HTTP status codes and responses

```python
from eden import Eden, Model, StringField, BoolField, Request

app = Eden(title="REST API", debug=True, secret_key="demo")
app.state.database_url = "sqlite+aiosqlite:///tasks.db"

# Define model
class Task(Model):
    """Simple task model."""
    title = StringField(max_length=200)
    completed = BoolField(default=False)

# List all tasks
@app.get("/tasks")
async def list_tasks():
    tasks = await Task.all()
    return {"tasks": [{"id": t.id, "title": t.title, "completed": t.completed} for t in tasks]}

# Create new task
@app.post("/tasks")
async def create_task(request: Request):
    data = await request.json()
    task = await Task.create(title=data.get("title", "Untitled"))
    return {"id": task.id, "title": task.title}

# Get single task
@app.get("/tasks/{task_id:int}")
async def get_task(task_id: int):
    task = await Task.get(task_id)
    return {"id": task.id, "title": task.title, "completed": task.completed}

# Update task
@app.put("/tasks/{task_id:int}")
async def update_task(task_id: int, request: Request):
    task = await Task.get(task_id)
    data = await request.json()
    if "title" in data:
        task.title = data["title"]
    if "completed" in data:
        task.completed = data["completed"]
    await task.save()
    return {"id": task.id, "title": task.title}

# Delete task
@app.delete("/tasks/{task_id:int}")
async def delete_task(task_id: int):
    await Task.delete(task_id)
    return {"deleted": True}
```

**Try it**:
```bash
eden run examples/02_rest_api.py

# In another terminal:
curl -X GET http://localhost:8000/tasks
curl -X POST http://localhost:8000/tasks -d '{"title":"Buy milk"}' -H "Content-Type: application/json"
curl -X GET http://localhost:8000/tasks/1
curl -X PUT http://localhost:8000/tasks/1 -d '{"completed":true}' -H "Content-Type: application/json"
curl -X DELETE http://localhost:8000/tasks/1
```

**Concepts**: ORM models, database connections, request bodies, path parameters, CRUD operations

**When to use**: Building data-driven APIs, working with databases

---

### 3️⃣ Web App — Templates & Forms (20 minutes)

**File**: `examples/03_web_app.py`

Creating a traditional web application:
- HTML template rendering with Jinja2
- HTML form handling
- GET → POST → redirect flow
- Using sessions for state management

```python
from eden import Eden, Model, StringField, Request, render_template

app = Eden(title="Web App", debug=True, secret_key="demo")
app.state.database_url = "sqlite+aiosqlite:///notes.db"

class Note(Model):
    """A simple note."""
    title = StringField(max_length=200)
    content = StringField(default="")

@app.get("/")
async def index():
    """Show all notes."""
    notes = await Note.all()
    return render_template("notes_list.html", {"notes": notes})

@app.post("/notes")
async def create_note(request: Request):
    """Handle form submission."""
    form = await request.form()
    note = await Note.create(
        title=form.get("title", "Untitled"),
        content=form.get("content", "")
    )
    return {"redirect": f"/notes/{note.id}"}

if __name__ == "__main__":
    app.setup_defaults()
    app.run(port=8000)
```

**Concepts**: Template rendering, form parsing, request/response handling

**When to use**: Building server-rendered web applications, full-stack projects

---

### 4️⃣ Authentication — Login & Sessions (25 minutes)

**File**: `examples/04_authentication.py`

Implementing user authentication:
- User model with password hashing
- Login endpoint with credentials
- `@login_required` decorator for protection
- Session-based authentication
- Protecting dashboard routes

```python
from eden import Eden, Model, StringField, Request, login_required, render_template

app = Eden(title="Auth App", debug=True, secret_key="super-secret")
app.state.database_url = "sqlite+aiosqlite:///auth.db"

# Define user model
class User(Model):
    username = StringField(max_length=100, unique=True)
    email = StringField(max_length=200)
    password_hash = StringField()

# Public route
@app.get("/")
async def index():
    return render_template("index.html")

# Login endpoint
@app.post("/login")
async def login(request: Request):
    form = await request.form()
    # In real app: hash password, lookup user, verify
    request.session["user_id"] = 1  # Store in session
    return {"message": "Logged in"}

# Protected route
@app.get("/dashboard")
@login_required
async def dashboard(request: Request):
    """Only accessible if logged in."""
    user_id = request.session.get("user_id")
    return render_template("dashboard.html", {"user_id": user_id})

# Logout endpoint
@app.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return {"message": "Logged out"}

if __name__ == "__main__":
    app.setup_defaults()
    app.run(port=8000)
```

**Key Points**:
- `@login_required`: Decorator that checks if user is authenticated
- `request.session`: Dictionary-like object for session data
- Sessions are encrypted with `secret_key`
- Password hashing: Use `argon2-cffi` library in production

**Concepts**: Password hashing, sessions, decorators, middleware, protected routes

**When to use**: Any app requiring user accounts, admin panels, membership sites

---

### 5️⃣ Advanced ORM — Relationships & Queries (30 minutes)

**File**: `examples/05_advanced_orm.py`

Mastering the ORM for complex scenarios:
- ForeignKeyField relationships between models
- Understanding N+1 query problems
- `prefetch_related()` for eager loading
- Complex filters with `F()` and `Q()`
- `order_by()`, `limit()`, and aggregations
- Understanding query execution

```python
from eden import Eden, Model, StringField, IntField, ForeignKeyField, F

app = Eden(title="Advanced ORM", debug=True, secret_key="demo")
app.state.database_url = "sqlite+aiosqlite:///blog.db"

class Author(Model):
    """Blog author."""
    name = StringField(max_length=200)
    email = StringField()

class Post(Model):
    """Blog post with author."""
    title = StringField(max_length=200)
    content = StringField()
    views = IntField(default=0)
    author_id = ForeignKeyField(Author)

@app.get("/posts")
async def list_posts():
    """Get all posts with eager-loaded authors (N+1 prevention)."""
    posts = await Post.select().prefetch_related("author").all()
    return {"posts": posts}

@app.get("/posts/popular")
async def popular_posts():
    """Get top 5 posts by view count."""
    posts = await Post.select().order_by("-views").limit(5).all()
    return {"posts": posts}

@app.post("/posts/{post_id:int}/view")
async def increment_views(post_id: int):
    """Increment view counter using F() expressions."""
    post = await Post.get(post_id)
    post.views = F("views") + 1
    await post.save()
    return {"views": post.views}

if __name__ == "__main__":
    app.setup_defaults()
    app.run(port=8000)
```

**Concepts**: Relationships, eager loading, query optimization, ORM advanced patterns

**When to use**: Building apps with complex data relationships, optimizing database performance

---

### 6️⃣ Multi-Tenancy — SaaS Patterns (35 minutes)

**File**: `examples/06_multi_tenant.py`

Building SaaS applications with data isolation:
- TenantMixin for automatic row-level security
- Using `request.tenant` to identify the tenant
- Automatic filtering by organization
- Understanding data isolation strategies
- Preventing cross-tenant data leaks

```python
from eden import Eden, Model, StringField, IntField, ForeignKeyField, TenantMixin

app = Eden(title="Multi-Tenant SaaS", debug=True, secret_key="demo")
app.state.database_url = "sqlite+aiosqlite:///saas.db"

# Enable multi-tenancy middleware
app.add_middleware("tenant")

# Organization model
class Organization(Model):
    """SaaS tenant - maps to Tenant in Eden."""
    name = StringField(max_length=200)
    domain = StringField()

# User model with tenant isolation
class User(Model, TenantMixin):
    """User belongs to an organization."""
    name = StringField(max_length=200)
    email = StringField()
    organization_id = ForeignKeyField(Organization)

# Document model with tenant isolation
class Document(Model, TenantMixin):
    """Document isolated per organization."""
    title = StringField(max_length=200)
    content = StringField()
    owner_id = ForeignKeyField(User)
    organization_id = ForeignKeyField(Organization)

# List documents - auto-filtered by organization
@app.get("/documents")
async def list_documents(request):
    """
    TenantMixin automatically filters by organization_id.
    Users only see their org's documents.
    """
    org_id = request.tenant.id
    docs = await Document.filter(organization_id=org_id).all()
    return {"documents": docs}

# Create document - auto-assigned to current org
@app.post("/documents")
async def create_document(request):
    """
    organization_id automatically set by TenantMixin.
    Document implicitly belongs to requesting user's org.
    """
    data = await request.json()
    doc = await Document.create(
        title=data["title"],
        content=data["content"],
        owner_id=request.user.id,
        organization_id=request.tenant.id  # Enforced
    )
    return {"id": doc.id, "title": doc.title}

if __name__ == "__main__":
    app.setup_defaults()
    app.run(port=8000)
```

**Security Benefits**:
- Row-level isolation: One org cannot access another's data
- Automatic filtering: No need to manually filter by org
- Query safety: Impossible to accidentally leak cross-tenant data
- Scalable: One database, multiple isolated orgs

**Concepts**: Multi-tenancy, data isolation, middleware context, query filtering

**When to use**: Building SaaS platforms, multi-user applications, shared infrastructure

---

### 7️⃣ Production Ready — Scaling Up (45 minutes)

**File**: `examples/07_production.py`

Bringing it all together for production deployment:
- Stripe payment integration patterns
- `@cache_view` decorator for performance
- `@app.task()` for background jobs
- Health check endpoints for load balancers
- Startup and shutdown hooks for initialization
- Environment variable configuration
- Production deployment checklist

```python
from eden import Eden, Model, StringField, IntField, cache_view, Request
import os

app = Eden(
    title="Production App",
    version="1.0.0",
    debug=False,
    secret_key=os.getenv("SECRET_KEY", "dev-only-key")
)
app.state.database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///app.db")

class Product(Model):
    name = StringField(max_length=200)
    price = IntField()  # in cents

@app.get("/products")
@cache_view(ttl=300)  # Cache for 5 minutes
async def list_products():
    """Cached product list for performance."""
    products = await Product.all()
    return {"products": products}

@app.post("/checkout")
async def checkout(request: Request):
    """Stripe checkout integration."""
    data = await request.json()
    # Create Stripe session, save order, etc.
    return {"status": "checkout_initiated"}

@app.task()
async def send_order_confirmation(order_id: int):
    """Background task: send confirmation email."""
    # from eden.mail import send_mail
    # await send_mail(...)
    pass

@app.get("/health")
async def health_check():
    """Health check for load balancers."""
    return {"status": "healthy", "version": app.version}

@app.on_startup
async def startup():
    print("🚀 Initializing production app...")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
```

**Concepts**: Caching strategies, background jobs, monitoring, deployment, integrations

**When to use**: Deploying to production, adding payment processing, scaling applications

---

## Recommended Learning Order

Follow this progression in order:

1. **Day 1**: Examples 1-2 (30 minutes)
   - Understand routing and basic CRUD
   - Get comfortable with async/await

2. **Day 1-2**: Examples 3-4 (45 minutes)
   - Build a complete web application
   - Add user authentication

3. **Day 2-3**: Example 5 (30 minutes)
   - Optimize database queries
   - Master database relationships

4. **Day 3-4**: Example 6 (35 minutes)
   - If building SaaS: Implement multi-tenancy
   - If not: Skip to Example 7

5. **Day 4-5**: Example 7 (45 minutes)
   - Add production features
   - Review deployment patterns

**Total time**: ~3-5 hours to understand all concepts

---

## Running the Examples

### Option 1: Copy the Example Code

Each example is self-contained. Copy the code into your project:

```bash
# Create project
eden new my_app --profile=minimal
cd my_app

# Copy example code from examples/ directory
cp ../examples/02_rest_api.py .
python -m uvicorn 02_rest_api:app --reload
```

### Option 2: Run Examples Directly

If you have the Eden repository cloned:

```bash
cd examples
python -m uvicorn 01_hello:app --reload
# Then: 02_rest_api, 03_web_app, etc.
```

---

## Getting Help While Learning

### Documentation Quick Links

- **[Routing Guide](../guides/routing.md)** - Deep dive into request handling
- **[ORM Guide](../guides/orm.md)** - Master database queries and relationships
- **[Forms & Validation](../guides/forms.md)** - Complete validation reference
- **[Templating Guide](../guides/templating.md)** - Template syntax and patterns
- **[Authentication Guide](../guides/auth.md)** - Security patterns and RBAC

### Troubleshooting Common Issues

**Q: My async function is slow**
- A: Check for N+1 queries. Use `prefetch_related()` for relationships.

**Q: CSRF token validation failing**
- A: Add `@csrf` directive to your template forms. See [Templating Guide](../guides/templating.md).

**Q: Can't connect to database**
- A: Check `DATABASE_URL` env var. Use `sqlite+aiosqlite:///db.sqlite3` for local development.

**Q: Port 8000 is already in use**
- A: Use different port: `app.run(port=8001)` or `eden run --port 8001`

**Q: Module import errors**
- A: Activate virtual environment: `source .venv/bin/activate`

---

## What's Next?

After completing Examples 1-7:

1. **Build a Side Project** - Apply all concepts to a real problem
2. **Read Advanced Guides** - Explore security, performance, deployment
3. **Deploy to Production** - Follow [Deployment Guide](../guides/deployment.md)
4. **Join Community** - Share your project and get feedback

---

**Happy Learning! 🌿**

For detailed step-by-step guidance, move to [Task Tutorials](../tutorial/task1_setup.md).

---

## How to Use Examples Effectively

1. **Run the example** to see it in action
2. **Read the docstring** to understand the concept
3. **Modify the code** - change field names, add routes, experiment
4. **Refer to API docs** when you need detail on specific concepts
5. **Move to the next example** once comfortable

---

## Common Progression Paths

### Path 1: REST API Developer
Examples 1 → 2 → 5 → 7
- Focus on API design and database optimization
- Skip web/template examples

### Path 2: Full-Stack Web Developer
Examples 1 → 2 → 3 → 4 → 5 → 7
- Learn all fundamentals in order
- Complete learning path

### Path 3: SaaS/Multi-Tenant Platform
Examples 1 → 2 → 4 → 5 → 6 → 7
- Add authentication early
- Focus on multi-tenancy in Example 6

### Path 4: Quick Start Only
Examples 1 → 2 → 7
- Jump straight to production patterns
- Review others as needed

---

## What's NOT Covered

These examples focus on core framework concepts. For advanced topics, see the API documentation:

- **WebSockets** → See [WebSocket Guide](../guides/websockets.md)
- **Admin Interface** → See [Admin Panel](../guides/admin.md)
- **Tenancy** → See [Multi-Tenancy Guide](../guides/tenancy.md)
- **Caching** → See [Caching Strategy](../guides/caching.md)
- **Testing** → See [Testing Guide](../tutorial/task10_testing.md)
- **Deployment** → See [Deployment Guide](../guides/deployment.md)

---

## Tips for Success

✅ **Do:**
- Run each example before reading code
- Modify examples to experiment
- Write your own small variations
- Read the "What you learned" section
- Take breaks between examples

❌ **Don't:**
- Read examples without running them
- Skip to advanced examples
- Copy-paste without understanding
- Memorize syntax (focus on concepts)
- Ignore error messages

---

## Getting Help

If you get stuck on an example:

1. **Check the docstring** - explains key concepts
2. **Read the API documentation** - detailed reference
3. **Review the "What you learned" section** - concepts summary
4. **Ask on community channels** - Discord, GitHub discussions

---

**Ready?** Start by exploring the [Example Snippets](example-snippets.md) or look into the `examples/` directory in the root of the project.
