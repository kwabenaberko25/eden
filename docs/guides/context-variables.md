# Context Variables in Eden 🔗

Context variables enable you to access the current request and user anywhere in your async code without passing them as function arguments. This guide covers the patterns, use cases, and best practices.

## Overview

In traditional synchronous frameworks, you might store the request on a thread-local object. With async/await, Python's `contextvars` module provides async-safe storage that works across `await` boundaries.

Eden exposes three context variables:

```python
from eden.context import request, user, get_request, get_user
```

### Global Proxies

```python
# Access via proxy objects (recommended)
from eden.context import request, user

@app.get("/profile")
async def profile(react):
    print(request.user.email)      # Access request context
    print(user.username)            # Access user context
```

### Manual Access Functions

```python
# Or use explicit getter functions
from eden.context import get_request, get_user

@app.get("/profile")
async def profile(react):
    req = get_request()
    usr = get_user()
    if usr:
        print(f"User: {usr.username}")
```

---

## Understanding Context Variables

### How They Work

Python's `contextvars` automatically isolates values across async tasks:

```
Request A              Request B
  ↓                      ↓
set_request(A)        set_request(B)
set_user(user_a)      set_user(user_b)
  ↓                      ↓
async tasks           async tasks
  ↓                      ↓
get_request() → A     get_request() → B  ✓ Isolated!
get_user() → user_a   get_user() → user_b
```

Each request context is automatically isolated, even within concurrent async operations.

### The Token Pattern

Context variables use a token-based reset mechanism for safety:

```python
from eden.context import set_request, reset_request

@app.middleware
async def request_middleware(request, call_next):
    # Save token for cleanup
    token = set_request(request)
    
    try:
        response = await call_next(request)
        return response
    finally:
        # Always reset context, even on exception
        reset_request(token)
```

This pattern **guarantees** cleanup even during errors, preventing context leakage.

---

## Request Context

### Accessing the Current Request

```python
from eden.context import request, get_request

@app.get("/whoami")
async def whoami():
    # Via proxy (recommended)
    return {"method": request.method, "path": request.url.path}

@app.post("/data")
async def receive_data():
    # Via function
    req = get_request()
    body = await req.json()
    return {"received": body}
```

### Common Request Properties

```python
from eden.context import request

async def handle():
    # HTTP metadata
    print(request.method)          # GET, POST, etc.
    print(request.url.path)        # /api/users
    print(request.headers)         # Request headers

    # User & session data
    print(request.user)            # Authenticated user (or None)
    print(request.session)         # Session dict (if SessionMiddleware enabled)
    
    # Body data
    json_body = await request.json()
    form_body = await request.form()
    text_body = await request.body()  # Raw bytes
    
    # Scope access
    print(request.scope["type"])   # "http"
    print(request.scope["client"]) # (host, port)
```

### Request Context in Background Tasks

Background tasks run outside the request-response cycle but can still access request context during setup:

```python
from eden.context import set_request, request

@app.post("/send-email")
async def send_email(request):
    # Capture request context
    req_token = set_request(request)
    
    async def send_in_background():
        # Background task can still access request context
        user_email = request.user.email
        
        await send_email_async(user_email)
    
    # Schedule task
    app.add_task(send_in_background)
    
    return {"status": "email queued"}
```

---

## User Context

### Authentication Middleware Integration

Eden's authentication middleware automatically sets the user context:

```python
@app.get("/me")
async def profile():
    from eden.context import user
    
    if user:
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email
        }
    return {"message": "Not authenticated"}
```

### Check Authentication Status

```python
from eden.context import user

@app.get("/protected")
async def protected_route():
    if not user:
        return {"error": "Not authenticated"}, 401
    
    return {"message": f"Hello {user.username}!"}
```

### User Context in Middleware

```python
from starlette.middleware.base import BaseHTTPMiddleware
from eden.context import user, request

class HeaderInjectMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        
        # Add user info to response headers
        if user:
            response.headers["X-User-ID"] = str(user.id)
        
        return response
```

---

## Context Manipulation

### Manual Context Management

For testing, background jobs, or admin operations, manually set context:

```python
from eden.context import set_request, set_user, reset_request, reset_user
from eden.requests import Request

async def run_admin_task(user_obj):
    """Execute a task as if it's running in user's context."""
    
    # Create a mock request
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/admin/task",
    }
    mock_request = Request(scope, receive=None, send=None)
    
    # Set context
    req_token = set_request(mock_request)
    user_token = set_user(user_obj)
    
    try:
        # Code here sees the mocked context
        from eden.context import user
        print(f"Running as {user.username}")
        
        result = await some_function()
        return result
    finally:
        # Always cleanup
        reset_user(user_token)
        reset_request(req_token)
```

### Temporary Context Override

```python
from eden.context import set_request, set_user, reset_request, reset_user

async def impersonate_user(admin, target_user):
    """Temporarily act as another user."""
    
    # Save original context
    original_user_token = set_user(target_user)
    
    try:
        # Impersonated block
        await perform_action()
    finally:
        # Restore original
        reset_user(original_user_token)
```

---

## Dependency Injection with Context

### Using Context in Services

Services often depend on knowing the current user or request:

```python
from eden.context import user, request

class CartService:
    """Shopping cart operations for current user."""
    
    async def add_item(self, product_id: int, quantity: int):
        if not user:
            raise PermissionError("Must be authenticated")
        
        # Add to current user's cart
        cart = await Cart.get_or_create(user_id=user.id)
        await CartItem.create(
            cart_id=cart.id,
            product_id=product_id,
            quantity=quantity
        )
        
        return cart

# Use in routes
cart_service = CartService()

@app.post("/cart/items")
async def add_to_cart(request):
    body = await request.json()
    cart = await cart_service.add_item(
        product_id=body["product_id"],
        quantity=body["quantity"]
    )
    return {"cart": cart.dict()}
```

### Dependency Resolver Integration

Eden's dependency resolver automatically passes request context:

```python
from eden.dependencies import Depends

async def get_current_user():
    from eden.context import user
    if not user:
        raise PermissionError("Unauthorized")
    return user

@app.get("/profile")
async def profile(current_user = Depends(get_current_user)):
    # current_user is automatically resolved from context
    return {"user": current_user.dict()}
```

---

## Common Patterns

### Pattern 1: Request Logging

```python
import uuid
from eden.context import request

@app.middleware
async def add_request_id(request, call_next):
    request.state.request_id = str(uuid.uuid4())
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    
    return response

@app.get("/data")
async def get_data():
    from eden.context import request
    
    print(f"Request ID: {request.state.request_id}")
    return {}
```

### Pattern 2: Audit Logging

```python
from eden.context import request, user
from datetime import datetime

async def audit_log(action: str, resource: str, details: dict = None):
    """Log an action for the current user."""
    
    log_entry = {
        "timestamp": datetime.now(),
        "user_id": user.id if user else None,
        "action": action,
        "resource": resource,
        "ip_address": request.client.host if request else None,
        "details": details or {}
    }
    
    await AuditLog.create(**log_entry)

@app.post("/users/{user_id}")
async def update_user(user_id: int, request):
    body = await request.json()
    
    user_obj = await User.get(user_id)
    user_obj.update(**body)
    
    # Log the change
    await audit_log("update", f"users/{user_id}", body)
    
    return {"user": user_obj.dict()}
```

### Pattern 3: Tenant Context Integration

```python
from eden.context import request
from eden.tenancy import get_current_tenant

@app.get("/tenant-data")
async def tenant_data():
    tenant = await get_current_tenant(request)
    
    if not tenant:
        return {"error": "No tenant in context"}, 400
    
    # All queries automatically scoped to this tenant
    items = await Item.all()
    
    return {"tenant": tenant.name, "items": items}
```

### Pattern 4: Error Handling with Context

```python
from eden.context import request, user

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Log all exceptions with request/user context."""
    
    error_id = str(uuid.uuid4())
    
    logger.error(
        f"Error {error_id}",
        extra={
            "user_id": user.id if user else None,
            "method": request.method if request else None,
            "path": request.url.path if request else None,
            "exception": str(exc)
        }
    )
    
    return {
        "error": "Internal server error",
        "error_id": error_id  # For support tickets
    }, 500
```

---

## Testing with Context

### Setting Context in Tests

```python
import pytest
from eden.context import set_request, set_user, reset_request, reset_user
from eden.requests import Request

@pytest.fixture
async def authenticated_context(user):
    """Fixture that sets up authenticated context."""
    
    scope = {"type": "http", "method": "GET", "path": "/"}
    request = Request(scope, receive=None, send=None)
    request.state.user = user
    
    req_token = set_request(request)
    user_token = set_user(user)
    
    yield
    
    reset_user(user_token)
    reset_request(req_token)

async def test_protected_operation(authenticated_context):
    """Test that requires authenticated context."""
    from eden.context import user
    
    assert user is not None
    assert user.username == "test_user"
```

---

## Troubleshooting

### Problem: "Working outside of request context"

**Cause**: Accessing context outside the request lifecycle

```python
# ❌ Wrong
@app.startup
async def startup():
    print(request.url.path)  # RuntimeError: Working outside of request context

# ✓ Correct
@app.startup
async def startup():
    print("App starting up")  # Don't access context here
    
@app.get("/")
async def homepage():
    print(request.url.path)  # OK: Inside request
```

**Solution**: Only access context within request handlers or tasks spawned from requests.

### Problem: Context not available in background task

**Cause**: Background tasks run outside the original request context

```python
# ❌ Wrong
async def send_email():
    email = user.email  # RuntimeError

app.add_task(send_email())

# ✓ Correct
async def send_email(user_email):
    # Pass context as function argument
    await EmailService.send(user_email)

@app.post("/register")
async def register(request):
    body = await request.json()
    user = await User.create(**body)
    
    # Pass user email explicitly
    app.add_task(send_email(user.email))
    
    return {"user": user.dict()}
```

### Problem: Context leaking between requests

**Cause**: Tokens not properly reset

```python
# ❌ Wrong
@app.middleware
async def middleware(request, call_next):
    token = set_request(request)
    response = await call_next(request)
    # Missing: reset_request(token)
    return response

# ✓ Correct
@app.middleware
async def middleware(request, call_next):
    token = set_request(request)
    try:
        response = await call_next(request)
        return response
    finally:
        reset_request(token)  # Always runs
```

---

## API Reference

### Context Variables

```python
# Request context
get_request() -> Optional[Request]      # Get current request
set_request(request: Request) -> Token
reset_request(token: Token) -> None

# User context  
get_user() -> Optional[User]            # Get current user
set_user(user: User) -> Token
reset_user(token: Token) -> None

# App context
get_app() -> Optional[Eden]
set_app(app: Eden) -> Token

# Proxy objects
request                                 # ContextProxy for request
user                                    # ContextProxy for user
```

### ContextProxy

```python
class ContextProxy:
    """Transparently proxy attribute access to context-local object."""
    
    def __getattr__(name)       # Get attribute from context object
    def __setattr__(name, value) # Set attribute on context object  
    def __bool__()              # Check if context is set
    def __repr__()              # String representation
```

---

## Next Steps

- [Authentication Middleware](../guides/security.md#authentication) - Multi-backend auth
- [Dependency Injection](../guides/dependencies.md) - Automatic context resolution
- [Tenancy Context](tenancy.md) - Tenant-scoped operations
- [Testing & Mocking](../guides/testing.md) - Context in tests
