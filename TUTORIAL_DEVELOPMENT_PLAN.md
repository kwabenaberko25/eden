# Comprehensive Eden Framework Tutorial Plan

## Overview
This plan details the creation of an exhaustive, step-by-step tutorial for the Eden Framework. It is strictly based on the current source code implementation and uses descriptive task-based names. Every step includes code snippets, explanations, and alternative approaches.

---

## Task 1: Environment Setup & Project Scaffolding

**Goal**: Create a development environment and generate the standard Eden project structure.

### 1.1 Create Project Directory
**Action**: Open a terminal and create a folder for your project.
**Command**:
```bash
mkdir my_eden_app
cd my_eden_app
```
**Explanation**:
- `mkdir`: Creates a new directory.
- `cd`: Changes the current working directory.

### 1.2 Set Up Virtual Environment
**Action**: Isolate project dependencies.
**Option A: Using `uv` (Recommended)**:
```bash
uv venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Mac/Linux
```
**Option B: Using Standard Python**:
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Mac/Linux
```
**Explanation**:
A virtual environment prevents dependency conflicts between projects.

### 1.3 Install Eden Framework
**Action**: Install Eden from PyPI or local source.
**Option A: From PyPI (Production)**:
```bash
pip install eden-framework
```
**Option B: From Local Source (Development)**:
If modifying the framework itself:
```bash
pip install -e C:\ideas\eden
```
**Verification**:
```bash
pip list | grep eden-framework
# Windows:
pip list | findstr eden-framework
```
Expected output: `eden-framework 0.1.0`

### 1.4 Scaffold Project with CLI
**Action**: Use `eden new` to generate the standard project structure.
**Command**:
```bash
eden new my_eden_app
```
**Interactive Prompt**:
Select **SQLite** for simplicity (default).
```text
🗄️  Select Database Engine [sqlite]:
```
**Generated Structure**:
```text
my_eden_app/
├── app/
│   ├── __init__.py      # App factory
│   ├── models/          # Database models
│   ├── routes/          # Route handlers
│   └── settings.py      # Environment config
├── static/              # CSS, JS, Images
├── templates/           # HTML templates
├── tests/               # Pytest tests
├── Dockerfile           # Container definition
├── docker-compose.yml   # Local development with DB
├── .env.example         # Environment variable template
└── requirements.txt     # Python dependencies
```

**Alternative: Manual Structure**:
If not using `eden new`:
```bash
mkdir -p app/models app/routes static templates tests
touch app/__init__.py app/settings.py
```

### 1.5 Install Project Dependencies
**Action**: Install dependencies from `requirements.txt`.
**Command**:
```bash
pip install -r requirements.txt
```
**Explanation**:
This installs Eden, Uvicorn, Pytest, and database drivers.

---

## Task 2: Configure Application Core

**Goal**: Initialize the Eden app instance and configure the database.

### 2.1 Review App Factory
**File**: `app/__init__.py`
**Action**: Examine the generated `create_app` function.
**Code**:
```python
from eden import Eden, setup_logging
from .settings import DEBUG, SECRET_KEY, DATABASE_URL, LOG_LEVEL, LOG_FORMAT
from .routes import main_router

def create_app() -> Eden:
    # 1. Configure Logging
    setup_logging(level=LOG_LEVEL, json_format=(LOG_FORMAT == "json"))

    # 2. Initialize Eden App
    app = Eden(
        title="my_eden_app",
        debug=DEBUG
    )

    # 3. Include Routes
    app.include_router(main_router)

    # 4. Add Middleware
    app.add_middleware("security")
    app.add_middleware("ratelimit", max_requests=200, window_seconds=60)
    app.add_middleware("logging")

    # 5. Enable Health Checks
    app.enable_health_checks()

    return app

app = create_app()
```

**Breakdown**:
1.  **Logging**: Configures structured logging.
2.  **Eden Initialization**: Creates the app instance. `debug=True` enables the premium debug UI.
3.  **Routes**: Attaches the main router (defined in `app/routes/__init__.py`).
4.  **Middleware**: Adds security layers (CSRF, CORS, etc.) and rate limiting.
5.  **Health Checks**: Exposes `/health` and `/ready` endpoints.

### 2.2 Configure Environment Variables
**File**: `app/settings.py`
**Action**: Review the settings file.
**Code**:
```python
import os

# ── Core ─────────────────────────────────────────────────────────────────
DEBUG = os.getenv("EDEN_DEBUG", "true").lower() == "true"
SECRET_KEY = os.getenv("EDEN_SECRET_KEY", "generate-a-secure-key-for-prod")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///db.sqlite3")

# ── Security ─────────────────────────────────────────────────────────────
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")

# ── Logging ──────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG" if DEBUG else "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "text" if DEBUG else "json")
```

**Different Situations**:
- **Development**: Use `.env` file (not committed to git) to override defaults.
- **Production**: Set environment variables in your hosting provider (e.g., Heroku, AWS).

### 2.3 Run the Application
**Action**: Start the development server.
**Command**:
```bash
eden run
```
**Expected Output**:
```text
🌿 Eden v0.1.0
📡 Running on http://127.0.0.1:8000
🔄 Auto-reload: enabled
```

**Verification**:
Open `http://127.0.0.1:8000`. You should see: `{"message": "Welcome to my_eden_app! 🌿"}`

---

## Task 3: Define Data Models (ORM)

**Goal**: Create database models using Eden's ORM helpers.

### 3.1 Create a User Model
**Action**: Use `eden generate model` or create manually.
**Option A: Using CLI (Recommended)**:
```bash
eden generate model User
```
**Option B: Manual Creation**:
**File**: `app/models/user.py`
**Code**:
```python
from eden.db import Model, f
from sqlalchemy.orm import Mapped

class User(Model):
    """
    User model.
    """
    # Use f() for simple fields. Type hints are auto-mapped.
    name: Mapped[str] = f(max_length=255)
    email: Mapped[str] = f(max_length=255, unique=True)
    
    # Use f(json=True) for dict/list data
    # payload: dict = f(json=True)
```

**Update `app/models/__init__.py`**:
```python
from .user import User
```

### 3.2 Database Migrations (Auto-Create Tables)
**Action**: Eden automatically creates tables on startup for SQLite.
**Verification**:
1.  Stop the server (`Ctrl+C`).
2.  Check if `db.sqlite3` exists in the root directory.
3.  Restart the server (`eden run`).
4.  The table `users` should be created.

**Manual Migration (Alembic)**:
For production, use Alembic (included in Eden).
```bash
# Initialize Alembic (if not already done)
eden generate migrations
# Apply migrations
eden db migrate
```

### 3.3 CRUD Operations
**Action**: Perform Create, Read, Update, Delete operations in the Python shell.

**Open Python Shell**:
```bash
python
```

**Code to Execute**:
```python
import asyncio
from app import create_app
from app.models import User

app = create_app()

async def test_crud():
    # 1. Create a User
    new_user = await User.create(name="Alice", email="alice@example.com")
    print(f"Created: {new_user}")

    # 2. Read Users
    users = await User.all()
    print(f"All Users: {users}")

    # 3. Filter Users
    alice = await User.get(email="alice@example.com")
    print(f"Found Alice: {alice}")

    # 4. Update User
    await alice.update(name="Alice Smith")
    print(f"Updated Name: {alice.name}")

    # 5. Delete User
    await alice.delete()
    print("User deleted")

asyncio.run(test_crud())
```

---

## Task 4: Build HTTP Routes & Views

**Goal**: Handle HTTP requests and return responses.

### 4.1 Create a Router
**Action**: Use `eden generate route` or create manually.
**Option A: Using CLI (Recommended)**:
```bash
eden generate route user
```
**Option B: Manual Creation**:
**File**: `app/routes/user.py`
**Code**:
```python
from eden import Router

user_router = Router()

@user_router.get("/")
async def index():
    return {"message": "Hello from user router! 🌿"}
```

**Update `app/routes/__init__.py`**:
```python
from .user import user_router
main_router.include_router(user_router)
```

### 4.2 Handle Request Data
**Action**: Access path parameters, query parameters, and request body.
**Code** (`app/routes/user.py`):
```python
from eden import Router, Response, status
from app.models import User

user_router = Router()

@user_router.get("/users")
async def list_users():
    users = await User.all()
    return [user.to_dict() for user in users]

@user_router.get("/users/{user_id}")
async def get_user(user_id: str):
    user = await User.get(id=user_id)
    if not user:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    return user.to_dict()

@user_router.post("/users")
async def create_user(request):
    data = await request.json()
    user = await User.create(**data)
    return user.to_dict()
```

### 4.3 Sub-Routers & Prefixes
**Action**: Organize routes using `Router` and `app.include_router()`.
**Code** (`app/routes/__init__.py`):
```python
from eden import Router
main_router = Router()

# Include user router with prefix
main_router.include_router(user_router, prefix="/api")
```

---

## Task 5: Implement Premium UI with Templating

**Goal**: Render HTML pages using Eden's directive-based templating.

### 5.1 Create a Base Template
**Action**: Create a layout template to avoid repetition.
**File**: `templates/layouts/base.html`
**Code**:
```html
<!DOCTYPE html>
<html>
<head>
    <title>@yield("title", "My App")</title>
</head>
<body>
    <nav>
        <a href="/">Home</a>
        <a href="/users">Users</a>
    </nav>
    <main>
        @yield("content")
    </main>
</body>
</html>
```

### 5.2 Create a Page Template
**Action**: Extend the base template and fill content.
**File**: `templates/users.html`
**Code**:
```html
@extends("layouts/base")

@section("title", "User List")

@section("content")
    <h1>Users</h1>
    <ul>
        @for (user in users) {
            <li>{{ user.name }} - {{ user.email }}</li>
        } @empty {
            <li>No users found.</li>
        }
    </ul>
@endsection
```

### 5.3 Render Template from View
**Action**: Return a template response.
**Code** (`app/routes/user.py`):
```python
from eden.templating import EdenTemplates

templates = EdenTemplates(directory="templates")

@user_router.get("/users")
async def list_users_html():
    users = await User.all()
    return templates.template_response("users.html", {"users": users})
```

**Alternative: Using App's Template Property**:
```python
@user_router.get("/users")
async def list_users_html(request):
    users = await User.all()
    # Access app instance via request
    app = request.app.eden
    return app.render("users.html", {"users": users})
```

---

## Task 6: Handle Forms & Validation

**Goal**: Validate user input using Pydantic.

### 6.1 Define a Pydantic Schema
**Action**: Create a schema for user creation.
**File**: `app/schemas/user.py`
**Code**:
```python
from pydantic import BaseModel, EmailStr, Field, validator

class UserSchema(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    age: int = Field(None, ge=18, le=120)

    @validator('name')
    def name_must_be_title_case(cls, v):
        if not v.istitle():
            raise ValueError('Name must be title case')
        return v
```

### 6.2 Integrate Form in View
**Action**: Process form submissions and validation.
**Code** (`app/routes/user.py`):
```python
from app.schemas.user import UserSchema

@user_router.post("/users")
async def create_user(request):
    data = await request.json()
    try:
        validated_data = UserSchema(**data)
        user = await User.create(**validated_data.dict())
        return user.to_dict()
    except ValueError as e:
        return {"error": str(e)}
```

**Alternative: Using Eden Forms**:
```python
from eden.forms import BaseForm

class UserForm(BaseForm):
    schema = UserSchema

@user_router.post("/users")
async def create_user(request):
    form_data = await request.form()
    form = UserForm(data=form_data)
    
    if form.is_valid():
        await User.create(**form.data)
        return redirect("/users")
    
    return templates.template_response("create_user.html", {"form": form})
```

---

## Task 7: Secure Application with Middleware & RBAC

**Goal**: Add security layers and role-based access control.

### 7.1 Add Middleware
**Action**: Configure middleware in `app/__init__.py`.
**Code**:
```python
def create_app() -> Eden:
    app = Eden(...)
    
    # Security middleware
    app.add_middleware("security")  # CSP, HSTS, XSS Protection
    app.add_middleware("csrf")      # Cross-Site Request Forgery
    app.add_middleware("ratelimit", max_requests=60, window_seconds=60)
    app.add_middleware("cors", allow_origins=["*"])
    
    return app
```

### 7.2 Protect Routes with RBAC
**Action**: Use decorators to restrict access.
**Code**:
```python
from eden.auth import roles_required, login_required

@user_router.get("/admin")
@roles_required(["admin"])
async def admin_dashboard():
    return {"message": "Admin access granted"}
```

**Alternative: API Key Authentication**:
```python
from eden import APIKey

# Generate a key
key_obj, raw_key = await APIKey.generate(user_id=user.id, name="Server Key")
# Use in requests: Authorization: Bearer <raw_key>
```

---

## Task 8: Integrate SaaS Features

**Goal**: Add admin panel, mail, storage, and payments.

### 8.1 Mount Admin Panel
**Action**: Register models and mount the admin interface.
**Code** (`app/__init__.py`):
```python
from eden.admin import admin

# Register models
admin.register(User)

# Mount at /admin
app.mount_admin()
```
**Verification**: Visit `http://127.0.0.1:8000/admin`.

### 8.2 Configure Mail Service
**Action**: Setup email backend.
**Code** (`app/__init__.py`):
```python
from eden.mail import SMTPBackend

# Use SMTP for production
smtp_backend = SMTPBackend(
    host="smtp.gmail.com",
    port=587,
    username="your-email@gmail.com",
    password="your-password"
)
app.configure_mail(smtp_backend)
```

**Send Email**:
```python
from eden import send_mail

await send_mail(
    subject="Welcome!",
    recipient="user@example.com",
    template="emails/welcome.html",
    context={"name": "John Doe"}
)
```

### 8.3 Setup S3 Storage
**Action**: Configure cloud storage.
**Code**:
```python
from eden import storage, S3StorageBackend

storage.register("s3", S3StorageBackend(
    bucket="my-bucket",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region="us-east-1"
))

# Save a file
url = await storage.save("avatars/user1.jpg", file_content)
```

### 8.4 Integrate Stripe Payments
**Action**: Setup Stripe provider.
**Code**:
```python
from eden import StripeProvider

stripe_provider = StripeProvider(api_key=os.getenv("STRIPE_SECRET_KEY"))
app.configure_payments(stripe_provider)
```

---

## Task 9: Deploy Application

**Goal**: Prepare for production deployment.

### 9.1 Docker Configuration
**Action**: Use the generated `Dockerfile`.
**Dockerfile**:
```dockerfile
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /install /usr/local
COPY . .
RUN adduser --disabled-password --no-create-home eden
USER eden
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
CMD ["eden", "run", "--host", "0.0.0.0", "--no-reload", "--app", "app:app"]
```

**Build and Run**:
```bash
docker build -t my-eden-app .
docker run -p 8000:8000 my-eden-app
```

### 9.2 Production Server (Gunicorn)
**Action**: Use Gunicorn with Uvicorn workers.
**Command**:
```bash
gunicorn app:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 9.3 Environment Variables
**Action**: Create a `.env` file for production secrets.
**File**: `.env`
```env
EDEN_DEBUG=false
SECRET_KEY=your-super-secret-key
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
AWS_ACCESS_KEY_ID=...
STRIPE_SECRET_KEY=...
```

---

## Task 10: Test & Automate

**Goal**: Ensure code quality with tests and CI/CD.

### 10.1 Write Unit Tests
**Action**: Test models and routes.
**File**: `tests/test_users.py`
**Code**:
```python
import pytest
from app.models import User

@pytest.mark.asyncio
async def test_user_creation():
    user = await User.create(name="Test User", email="test@example.com")
    assert user.name == "Test User"
    assert user.email == "test@example.com"
    
    # Cleanup
    await user.delete()
```

### 10.2 Integration Tests
**Action**: Test HTTP endpoints.
**File**: `tests/test_routes.py`
**Code**:
```python
import pytest
from httpx import ASGITransport, AsyncClient
from app import app

@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c

@pytest.mark.asyncio
async def test_index(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert "Welcome" in resp.json()["message"]
```

### 10.3 CI/CD Pipeline
**Action**: Create GitHub Actions workflow.
**File**: `.github/workflows/ci.yml`
**Code**:
```yaml
name: CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with: { python-version: "3.11" }
      - run: pip install -r requirements.txt
      - run: pytest
```

---

## Documentation Structure

**Action**: Create markdown files for each task in `docs/source/`.
**Files to Create**:
- `docs/source/task1_environment_setup.md`
- `docs/source/task2_app_configuration.md`
- `docs/source/task3_data_models.md`
- `docs/source/task4_routes_views.md`
- `docs/source/task5_templating.md`
- `docs/source/task6_forms_validation.md`
- `docs/source/task7_security_middleware.md`
- `docs/source/task8_saas_features.md`
- `docs/source/task9_deployment.md`
- `docs/source/task10_testing_automation.md`

**Update `docs/source/index.md`**:
```markdown
## 🚀 Eden Tutorial (Task-Based)

```{toctree}
:caption: Tutorial
:maxdepth: 2
:numbered:

task1_environment_setup
task2_app_configuration
task3_data_models
task4_routes_views
task5_templating
task6_forms_validation
task7_security_middleware
task8_saas_features
task9_deployment
task10_testing_automation
```
```

---

## Next Steps

1.  **Create Files**: Generate the markdown files for each task.
2.  **Populate Content**: Copy the code snippets and explanations from this plan.
3.  **Build Docs**: Run `mkdocs build` or `sphinx-build` to verify.
4.  **Review**: Check for broken links and syntax errors.
