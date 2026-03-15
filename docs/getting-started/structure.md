# Project Structure 🏗️

A standard Eden project follows a clean, modular layout designed for both small sites and enterprise-grade SaaS applications.

## The Default Layout

When you run `eden new`, your project will follow a **Premium-Flat** layout:

```text
my_project/
├── app.py          # App initialization & middleware (Premium)
├── models.py       # Domain models
├── settings.py     # Application settings
├── routes/         # Routes package
│   └── __init__.py # Main router
├── static/         # CSS, JS, Images
├── templates/      # HTML templates (@directives)
├── tests/          # Pytest suite
│   └── conftest.py # Test configuration
├── .env.example    # Environment template
├── Dockerfile      # Container config
└── docker-compose.yml
```

## Core Configuration

### `.env`
Your project secrets and environment-specific toggles live here. Eden automatically loads these into `app.config`.

```text
DEBUG=True
SECRET_KEY=y0ur-5ecr3t-k3y
DATABASE_URL=sqlite+aiosqlite:///db.sqlite3
```

### `eden.json`
This file contains framework-level metadata used by **The Forge** and the CLI to manage your project's identity and dependencies.

## Core Files Explained

### `app.py`
The "heart" of your application. This is where you instantiate `Eden`, configure the middleware stack (Security, Session, CSRF, etc.), and mount your routers.

### `models.py`
Domain models inheriting from `Model` live here. By default, Eden provides a flat `models.py` for simplicity, but you can convert this to a package as your domain grows.

### `settings.py`
Global application settings and environment-variable lookups. This file keeps your `app.py` clean by separating configuration from initialization logic.

### `/routes`
We recommend grouping related routes into this package. Use the `Router` class to create modular endpoints that are then mounted in `app.py`.

### `/static`
Files placed here are served automatically. In production, we recommend serving these via a CDN or a web server like Nginx, but Eden handles them natively for development.

## Scalability Patterns

As your project grows, use these organizational patterns to maintain clarity:

### Pattern 1: Modular Routes by Domain

For larger applications, organize routes by feature domain:

```text
my_project/
├── app.py                    # Main entry point
├── models.py                 # All models
├── routes/
│   ├── __init__.py          # Main router that includes sub-routers
│   ├── users.py             # User-related endpoints
│   ├── posts.py             # Post-related endpoints
│   └── admin.py             # Admin endpoints
├── middleware/
│   ├── __init__.py
│   ├── auth.py              # Authentication logic
│   └── permissions.py       # Authorization/permission checks
├── schemas/
│   ├── __init__.py
│   ├── user.py              # User schemas
│   └── post.py              # Post schemas
├── static/
├── templates/
└── tests/
```

**Example**: `routes/__init__.py`
```python
from eden import Router
from .users import user_router
from .posts import post_router
from .admin import admin_router

main_router = Router()
main_router.include_router(user_router, prefix="/users")
main_router.include_router(post_router, prefix="/posts")
main_router.include_router(admin_router, prefix="/admin", name="admin")

# In app.py:
app.include_router(main_router)
```

### Pattern 2: Encapsulation with Resources

For complex domains, use **Resources** which combine Model, Router, Schema, and Admin view:

```python
# app/resources/user.py
from eden import Resource, Model, Router, Schema

class User(Model):
    name: str
    email: str
    is_active: bool = True

class UserSchema(Schema):
    name: str
    email: str

class UserResource(Resource):
    model = User
    schema = UserSchema
    router = Router(name="users", prefix="/users")
    
    # Resource automatically generates CRUD routes
    # GET /users/, POST /users/, GET /users/{id}, PUT /users/{id}, DELETE /users/{id}

# In app.py:
app.register_resource(UserResource())
```

### Pattern 3: Service Layer for Business Logic

Extract complex logic into service modules:

```text
my_project/
├── models.py
├── routes/
├── services/
│   ├── __init__.py
│   ├── user_service.py      # User-related business logic
│   └── email_service.py     # Email sending logic
```

**Example**: `services/user_service.py`
```python
from app.models import User
from app.services.email_service import send_welcome_email

class UserService:
    @staticmethod
    async def create_user(name: str, email: str, password: str):
        """Create user with all side effects (email, logging, etc)."""
        user = await User.create(
            name=name,
            email=email,
            password=password
        )
        
        # Send welcome email asynchronously
        await send_welcome_email(user)
        
        return user
    
    @staticmethod
    async def deactivate_user(user_id: int):
        """Properly deactivate a user and clean up related data."""
        user = await User.get(user_id)
        user.is_active = False
        await user.save()
        
        # Clean up sessions, cancel subscriptions, etc.
        await user.sessions.all().delete()
        
        return user
```

Then in routes:
```python
from app.services.user_service import UserService

@user_router.post("/")
async def create_user(request: Request, data: UserCreateSchema):
    user = await UserService.create_user(
        name=data.name,
        email=data.email,
        password=data.password
    )
    return user.to_dict()
```

### Pattern 4: Configuration & Environment

Keep configuration centralized:

```python
# settings.py
import os

class Config:
    """Base configuration."""
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-key")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///db.sqlite3")

class DevelopmentConfig(Config):
    """Development settings."""
    DEBUG = True
    LOG_LEVEL = "DEBUG"

class ProductionConfig(Config):
    """Production settings."""
    DEBUG = False
    LOG_LEVEL = "INFO"
    SESSION_TIMEOUT = 3600

# Use in app.py
environment = os.getenv("ENVIRONMENT", "development")
config = DevelopmentConfig if environment == "development" else ProductionConfig

app = Eden(
    debug=config.DEBUG,
    secret_key=config.SECRET_KEY
)
```

### Pattern 5: Testing Structure

Organize tests to mirror your application structure:

```text
tests/
├── conftest.py              # Fixtures and test setup
├── test_models.py           # Model unit tests
├── test_routes/
│   ├── test_users.py        # User endpoint tests
│   └── test_posts.py        # Post endpoint tests
├── test_services/
│   ├── test_user_service.py # User service tests
│   └── test_email_service.py
└── test_integration.py      # Full integration tests
```

---

**Next Steps**: [Routing Guide](../guides/routing.md)
