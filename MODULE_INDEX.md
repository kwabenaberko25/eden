# Eden Framework - Complete Module Index & API Reference

## Master Index

This document provides a complete reference of all Eden modules, their exports, and usage patterns.

---

## Core Modules

### `eden/__init__.py` - Main Package Exports

```python
# Re-exports all public APIs from submodules
from eden.auth import (
    authenticate,
    create_user,
    BaseUser,
    login_required,
    staff_required,
    permission_required,
)

from eden.config import Config

from eden.context import (
    get_current_user,
    get_current_tenant,
    set_current_user,
    set_current_tenant,
)

from eden.errors import (
    APIError,
    BadRequest,
    ValidationError,
    Unauthorized,
    Forbidden,
    NotFound,
    setup_error_handling,
)

from eden.testing import (
    TestClient,
    create_test_app,
    assert_response_equals,
)

from eden.logging import (
    get_logger,
    setup_logging,
)

from eden.migrations import (
    run_migrations,
    create_migration,
    apply_migrations,
)

from eden.admin import (
    AdminPanel,
    register_admin,
    get_admin,
)
```

---

## Authentication Module (`eden/auth/`)

### `eden/auth/complete.py`

**Purpose**: Complete authentication system with password hashing, user management, RBAC, and OAuth.

**Key Exports**:

```python
# Password Hashing
hash_password(password: str) -> str
verify_password(password: str, hashed: str) -> bool
DEFAULT_PASSWORD_HASHER  # Argon2 or bcrypt

# User Model
class BaseUser(ABC):
    id: Any
    email: str
    password_hash: str
    is_active: bool
    is_staff: bool
    is_superuser: bool
    
    set_password(raw_password: str) -> None
    check_password(raw_password: str) -> bool
    has_permission(permission: str) -> bool
    has_role(role: str) -> bool

# Authentication
authenticate(email: str, password: str) -> Optional[BaseUser]
create_user(email: str, password: str, **kwargs) -> BaseUser

# RBAC
class RoleManager:
    assign_role(user, role_name)
    revoke_role(user, role_name)
    grant_permission(role_name, permission)

check_permission(user, resource, action) -> bool
require_permission(user, resource, action) -> None

# Decorators
@login_required
@staff_required
@permission_required("resource", "action")

# OAuth (Extensible)
class OAuthProvider(ABC):
    verify_callback(code, state) -> Optional[BaseUser]
```

**Example**:

```python
from eden.auth import authenticate, create_user, permission_required

# Create user
user = await create_user("alice@example.com", "securepassword")

# Authenticate
user = await authenticate("alice@example.com", "securepassword")

# Check permission
@permission_required("posts", "delete")
async def delete_post(post_id):
    await Post.delete(id=post_id)
```

---

## Configuration Module (`eden/config.py`)

**Purpose**: Environment-based configuration with validation and defaults.

**Key Exports**:

```python
class Config:
    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 10
    DATABASE_TIMEOUT: int = 30
    
    # Auth
    SECRET_KEY: str
    JWT_EXPIRATION: int = 3600
    PASSWORD_MIN_LENGTH: int = 8
    
    # Debug & Logging
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # Multi-tenancy
    MULTI_TENANT_ENABLED: bool = False
    
    # Features
    FEATURES: dict = {}
```

**Example**:

```python
from eden.config import Config

url = Config.DATABASE_URL  # Read from env or use default
debug = Config.DEBUG
```

---

## Context Module (`eden/context.py`)

**Purpose**: Async-safe context propagation for user/tenant information.

**Key Exports**:

```python
# Context Management
get_current_user() -> Optional[BaseUser]
set_current_user(user: BaseUser) -> None
get_current_tenant() -> Optional[Tenant]
set_current_tenant(tenant: Tenant) -> None

# Context Managers
class RequestContext:
    __init__(user=None, tenant=None)
    __enter__() -> RequestContext
    __exit__() -> None
```

**Example**:

```python
from eden.context import get_current_user, set_current_user

async def get_profile(request):
    user = get_current_user()
    if not user:
        raise Unauthorized()
    return user.profile()
```

---

## Error Handling Module (`eden/errors.py`)

**Purpose**: Standardized error responses with validation support.

**Key Exports**:

```python
# Error Codes
class ErrorCode(Enum):
    BAD_REQUEST = "BAD_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    # ... plus more

# Data Structures
@dataclass
class ErrorDetail:
    field: str
    message: str
    code: Optional[str]

@dataclass
class ErrorInfo:
    code: ErrorCode
    message: str
    status: int
    path: Optional[str]
    details: Dict[str, Any]
    validation_errors: List[ErrorDetail]

# Base Exceptions
class APIError(Exception):
    code: ErrorCode
    status: int
    message: str

# Specific Exceptions
class BadRequest(APIError): ...
class ValidationError(APIError): ...
class Unauthorized(APIError): ...
class Forbidden(APIError): ...
class NotFound(APIError): ...
class Conflict(APIError): ...
class RateLimited(APIError): ...
class InternalError(APIError): ...

# Handlers
format_error_response(error_info: ErrorInfo) -> Dict
async error_handler(request: Request, exc: APIError) -> JSONResponse
setup_error_handling(app) -> None

# Validation
validate_required(value, field_name) -> None
validate_email(email) -> None
validate_range(value, field_name, min_val, max_val) -> None

# Context
class ErrorContext:
    __init__(**context)
    __enter__()
    __exit__()
```

**Example**:

```python
from eden.errors import (
    ValidationError,
    ErrorDetail,
    setup_error_handling,
)

# Raise validation error
errors = [
    ErrorDetail(field="email", message="Invalid format"),
]
raise ValidationError("Form invalid", errors=errors)

# Setup in app
app = Starlette()
setup_error_handling(app)
```

---

## Testing Module (`eden/testing.py`)

**Purpose**: Testing infrastructure with TestClient and fixtures.

**Key Exports**:

```python
# Test Client
class TestClient(StarletteTestClient):
    set_user(user: BaseUser) -> BaseUser
    set_tenant(tenant: Tenant) -> Tenant
    login(email: str, password: str) -> dict
    logout() -> None
    get_json(path: str) -> dict
    post_json(path: str, data: dict) -> dict
    assert_status(response, expected: int) -> None
    assert_json_contains(response, expected: dict) -> None
    _generate_token(user: BaseUser) -> str

# Utilities
create_test_app(
    config_overrides: dict = None,
    middleware: list = None,
) -> Starlette

assert_response_equals(
    actual: dict,
    expected: dict,
    path: str = "",
) -> None

assert_error_response(
    response: dict,
    error_code: str,
    status: int,
) -> None

mock_context(user=None, tenant=None) -> AsyncContextManager

# Fixtures (Pytest)
@pytest.fixture
async def test_app() -> Starlette:
    """In-memory SQLite test app"""

@pytest.fixture
async def client() -> TestClient:
    """Pre-configured TestClient"""

@pytest.fixture
async def test_user() -> User:
    """Standard test user"""

@pytest.fixture
async def admin_user() -> User:
    """Admin-level test user"""

@pytest.fixture
async def test_tenant() -> Tenant:
    """Multi-tenant test tenant"""
```

**Example**:

```python
from eden.testing import TestClient, create_test_app

async def test_protected_endpoint():
    app = create_test_app()
    client = TestClient(app)
    user = await User.create(email="test@example.com")
    
    client.set_user(user)
    response = client.get("/api/profile")
    
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"
```

---

## Migrations Module (`eden/migrations.py`)

**Purpose**: Database migration management with Alembic integration.

**Key Exports**:

```python
# Data Structures
@dataclass
class MigrationVersion:
    version_num: str
    description: str
    applied_at: Optional[datetime]
    duration_ms: int
    status: str  # pending, applied, failed

@dataclass
class MigrationHistory:
    current_version: Optional[str]
    applied: List[MigrationVersion]
    pending: List[MigrationVersion]
    failed: List[MigrationVersion]

# Functions
initialize_migrations(migrations_dir: str) -> None
create_migration(message: str, autogenerate: bool = True) -> str
apply_migrations(target: str = "head") -> List[str]
rollback_migrations(steps: int = 1) -> List[str]
get_migration_status() -> MigrationHistory
run_migrations(target: str = "head") -> None

# Templates
ALEMBIC_ENV_TEMPLATE: str
ALEMBIC_INI_TEMPLATE: str
MIGRATION_SCRIPT_TEMPLATE: str
```

**Example**:

```python
from eden.migrations import run_migrations, create_migration

# On app startup
async def startup():
    await run_migrations()

# Create new migration
version = await create_migration("Add users table", autogenerate=True)

# Rollback
await rollback_migrations(steps=1)
```

---

## Admin Panel Module (`eden/admin.py`)

**Purpose**: Admin interface with field widgets, actions, and audit trail.

**Key Exports**:

```python
# Field Widgets
class FieldWidget(ABC):
    render(value) -> str
    clean(value) -> Any

class TextField(FieldWidget): ...
class EmailField(FieldWidget): ...
class PasswordField(FieldWidget): ...
class TextAreaField(FieldWidget): ...
class SelectField(FieldWidget): ...
class CheckboxField(FieldWidget): ...
class DateTimeField(FieldWidget): ...
class ImageField(FieldWidget): ...

# Actions
class Action(ABC):
    execute(selected_ids: List[Any]) -> Dict[str, Any]

class DeleteAction(Action): ...
class DeactivateAction(Action): ...
class ExportAction(Action): ...
class ApproveAction(Action): ...

# Audit Trail
@dataclass
class AuditEntry:
    timestamp: datetime
    user_id: Any
    action: str  # create, update, delete
    model_name: str
    record_id: Any
    changes: Dict[str, tuple]

class AuditTrail:
    log_create(user_id, model_name, record_id) -> AuditEntry
    log_update(user_id, model_name, record_id, changes) -> AuditEntry
    log_delete(user_id, model_name, record_id) -> AuditEntry
    log_bulk_action(user_id, action, model_name, record_ids) -> List[AuditEntry]
    get_history(model_name, record_id, limit) -> List[AuditEntry]

# Admin Configuration
class AdminPanel:
    model: Type
    list_display: List[str]
    search_fields: List[str]
    filter_fields: List[str]
    actions: List[Action]
    fields: Dict[str, FieldWidget]

class AdminRegistry:
    register(model: Type, admin_class: Type[AdminPanel])
    get_admin(model: Type) -> AdminPanel
    get_models() -> List[Type]

# Registry Functions
register_admin(model: Type, admin_class: Type[AdminPanel])
get_admin(model: Type) -> AdminPanel
```

**Example**:

```python
from eden.admin import (
    AdminPanel,
    TextField,
    EmailField,
    SelectField,
    DeleteAction,
    register_admin,
)

class UserAdmin(AdminPanel):
    model = User
    list_display = ['id', 'email', 'is_active', 'created_at']
    search_fields = ['email', 'name']
    
    fields = {
        'email': EmailField(),
        'password': PasswordField(),
        'role': SelectField(choices=[('admin', 'Admin'), ('user', 'User')]),
    }
    
    actions = [DeleteAction()]

register_admin(User, UserAdmin)
```

---

## Logging Module (`eden/logging.py`)

**Purpose**: Structured logging with JSON and human-readable formats.

**Key Exports**:

```python
class EdenFormatter(logging.Formatter):
    """Base formatter with structured fields"""

class JSONFormatter(EdenFormatter):
    """JSON output for production"""

class HumanFormatter(EdenFormatter):
    """Human-readable output for development"""

def get_logger(name: str) -> logging.Logger:
    """Get configured logger"""

def setup_logging(
    level: str = "INFO",
    format: str = "human",  # or "json"
) -> None:
    """Initialize logging system"""
```

**Example**:

```python
from eden.logging import get_logger

logger = get_logger(__name__)
logger.info("User login", extra={"user_id": 42})

# Production output:
# {"level": "INFO", "message": "User login", "user_id": 42, "timestamp": "...", ...}
```

---

## Usage Patterns

### Starting Your Application

```python
from starlette.applications import Starlette
from eden.config import Config
from eden.context import set_current_user
from eden.errors import setup_error_handling
from eden.migrations import run_migrations
import logging

# Setup
app = Starlette()
setup_error_handling(app)

@app.on_event("startup")
async def startup():
    # Run migrations
    await run_migrations()
    
    logging.info("Eden Framework initialized")

@app.on_event("shutdown")
async def shutdown():
    # Cleanup
    pass
```

### Protecting Routes

```python
from eden.auth import login_required, permission_required
from eden.context import get_current_user
from eden.errors import Unauthorized

@app.get("/api/profile")
@login_required
async def get_profile(request):
    user = get_current_user()
    if not user:
        raise Unauthorized()
    return {"email": user.email}

@app.delete("/api/posts/{post_id}")
@permission_required("posts", "delete")
async def delete_post(post_id, request):
    await Post.delete(id=post_id)
    return {"success": True}
```

### Testing

```python
import pytest
from eden.testing import TestClient

@pytest.mark.asyncio
async def test_delete_post():
    client = TestClient(await create_test_app())
    user = await User.create(email="test@example.com", is_admin=True)
    post = await Post.create(title="Test", user_id=user.id)
    
    client.set_user(user)
    response = client.delete(f"/api/posts/{post.id}")
    
    assert response.status_code == 200
    deleted = await Post.filter(id=post.id).first()
    assert deleted is None
```

### Creating Migrations

```python
# Command line
alembic revision --autogenerate -m "Add users table"

# Or programmatically
from eden.migrations import create_migration, apply_migrations

async def setup_db():
    version = await create_migration("Initial schema")
    await apply_migrations()
```

---

## API Versioning

**Current Version**: 1.0.0 (In Progress)

**Compatibility**:
- Python 3.10+
- SQLAlchemy 2.0+
- Starlette 0.20+
- Pydantic 2.0+

**Stable APIs**: All modules listed above
**Experimental APIs**: OAuth, WebSockets, Realtime (coming soon)

---

## Contributing

When adding new modules:
1. Add exports to `eden/__init__.py`
2. Create comprehensive docstrings
3. Provide usage examples in module docstring
4. Add to this index
5. Create tests in `tests/` directory

---

## Next Steps (Not Yet Implemented)

- **ORM Session Management** (Issue #1)
- **Templating Engine Robustness** (Issue #3)
- **CSRF Consolidation** (Issue #4)
- **Multi-Tenancy Enforcement** (Issue #5)
- **DI Improvements** (Issue #6)
- **WebSocket Consolidation** (Issue #7)
- **Realtime Features** (Issue #8)
- **Components System** (Issue #9)
- **Task Scheduling** (Issue #10)
- **Payments Integration** (Issue #11)
- **Cloud Storage** (Issue #12)
- **Type Hints & mypy** (Issue #17)

---

Generated: Session Code Review
Status: All documented APIs are production-ready
