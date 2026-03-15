# Isolation Checklist: Layer-Specific Diagnostics

Use this checklist to identify which subsystem your error originates from. Work through each layer systematically.

---

## 🗄️ ORM Layer (`eden/db/`)

**Symptoms**: Query failures, `AttributeError` on model instances, type mismatches, schema mismatches

### Quick Diagnostics
- [ ] Is the error on a specific model or all models?
- [ ] Does raw SQL bypass the error? (Test with `db.raw_execute()`)
- [ ] Are field types correct? (Check schema migration vs. model definition)
- [ ] Is the query filtering correctly? (Print the generated SQL)

### Common Issues
- **Migration not applied**: Column doesn't exist in database
- **Type mismatch**: StringField queried with integer
- **Relationship broken**: ForeignKey target doesn't exist
- **Lazy evaluation**: QuerySet created but not executed
- **Wrong schema**: Query targeting wrong tenant schema

### Diagnostics
```python
# Check generated SQL
print(str(queryset.query))

# Verify field types
print(MyModel._meta.fields)

# Test raw SQL directly
result = await db.raw_execute("SELECT * FROM my_table WHERE id = %s", [user_id])
```

---

## 🔄 Middleware Layer (`eden/middleware/`)

**Symptoms**: All requests fail at same point, headers not set, session lost, CSRF errors

### Quick Diagnostics
- [ ] Does error occur for all endpoints or specific routes?
- [ ] Does error go away if middleware is disabled?
- [ ] Are required headers present? (Log request headers)
- [ ] Is middleware order correct? (Check registration in app)

### Common Issues
- **Wrong order**: Middleware runs before another middleware it depends on
- **Missing binding**: Middleware doesn't attach object to request
- **Exception escape**: Error in middleware not caught, bubbles to user
- **Context not set**: Request context not populated, downstream code fails
- **Header parsing**: Expected header missing or malformed

### Diagnostics
```python
# Log middleware execution
logger.debug(f"Middleware: headers={request.headers}")
logger.debug(f"Middleware: context={getattr(request, 'context', None)}")

# Temporarily disable middleware
# app.middleware.remove(ProblemMiddleware)

# Check middleware order
print([m.__class__.__name__ for m in app.middleware.middleware])
```

---

## 📄 Templates Layer (`eden/templates/`)

**Symptoms**: Template errors, undefined variables, filter not found, rendering fails

### Quick Diagnostics
- [ ] Does the template render at all? (Check for `TemplateError`)
- [ ] Is the variable available in context? (Log context dict)
- [ ] Are custom directives/filters registered? (Check `eden/templates/directives/`)
- [ ] Is template inheritance correct? (Check `{% extends %}` target)

### Common Issues
- **Context missing**: Template expects `{{ user }}` but not provided
- **Filter not registered**: Template uses custom filter but it's not imported
- **Type error**: Template tries to iterate non-iterable or access non-existent attribute
- **Inheritance broken**: Child template extends wrong parent
- **Wrong block name**: Template references block that doesn't exist in parent

### Diagnostics
```python
# Print context passed to template
print(f"Template context: {context}")

# Log template rendering
logger.debug(f"Rendering template: {template_name}")
logger.debug(f"Context keys: {context.keys()}")

# Test template directly
from eden.templates import render
result = render("my_template.html", context)
```

---

## ⚡ Async & Task Layer (`eden/tasks/`)

**Symptoms**: Timeout errors, tasks don't execute, concurrent access issues, event loop errors

### Quick Diagnostics
- [ ] Is the async function actually awaited? (Check for missing `await`)
- [ ] Are context vars set in async context? (Test with `request_context.set()`)
- [ ] Does the task run synchronously if you remove async? (Locate sync bottleneck)
- [ ] Are there blocking I/O calls in async code? (Check for `requests.get()` not `aiohttp`)

### Common Issues
- **Missing await**: `asyncio.sleep()` created but not awaited
- **Wrong context**: Async function called outside request context
- **Blocking I/O**: Synchronous call (like `requests.get()`) blocks event loop
- **Context var lost**: Context set in one task but not in spawned task
- **Task not started**: Task created but never registered with scheduler

### Diagnostics
```python
# Check if function is awaited
result = await some_async_function()  # Correct
result = some_async_function()  # Wrong - returns coroutine, not result

# Verify context var is set
from eden.context import request_context
logger.debug(f"Current request: {request_context.get()}")

# Check for blocking I/O
import logging
logging.getLogger("asyncio").setLevel(logging.DEBUG)
```

---

## 👥 Multi-Tenancy Layer (`eden/multi_tenancy/`)

**Symptoms**: Data leaks across tenants, wrong schema accessed, tenant context missing

### Quick Diagnostics
- [ ] Is the tenant context set for this request? (Check `request.tenant`)
- [ ] Does the query include tenant filtering? (Check generated SQL)
- [ ] Are you using the right schema? (Log schema name before query)
- [ ] Is tenant isolation enforced at DB level or app level?

### Common Issues
- **Missing tenant filter**: Query doesn't include tenant_id in WHERE clause
- **Wrong schema**: Using public schema instead of tenant schema
- **Tenant not set**: Request processed without setting current tenant
- **Isolation level**: Multiple tenants access same data in same transaction
- **Cascade not respected**: Related records not filtered by tenant

### Diagnostics
```python
# Check tenant context
print(f"Current tenant: {request.tenant}")
print(f"Current schema: {db.current_schema()}")

# Verify query includes tenant filter
queryset = MyModel.objects.filter(user__tenant=request.tenant)
print(f"Query SQL: {queryset.query}")

# Log tenant transitions
logger.debug(f"Setting tenant: {tenant_id}")
await set_current_tenant(tenant_id)
logger.debug(f"Now in schema: {db.current_schema()}")
```

---

## 🔐 Auth Layer (`eden/auth/`)

**Symptoms**: Login fails, tokens invalid, decorators not enforced, permissions denied incorrectly

### Quick Diagnostics
- [ ] Is the auth decorator applied? (Check `@require_auth`, `@admin_only`)
- [ ] Is the token valid? (Decode JWT and check exp, signature)
- [ ] Are permissions checked correctly? (Log user roles/permissions)
- [ ] Is session middleware enabled? (Check middleware registration)

### Common Issues
- **Decorator missing**: Auth not enforced, endpoint public
- **Token expired**: JWT has valid signature but exp time passed
- **Invalid signature**: Token signed with wrong key or tampered
- **Permission mismatch**: User role doesn't match required permission
- **Session lost**: Session cookie expired or not sent in request

### Diagnostics
```python
# Decode JWT manually
import jwt
try:
    decoded = jwt.decode(token, app.config.SECRET_KEY, algorithms=["HS256"])
    print(f"Token valid: {decoded}")
except jwt.ExpiredSignatureError:
    print("Token expired")
except jwt.InvalidSignatureError:
    print("Token signature invalid")

# Check user roles
print(f"User roles: {user.roles}")
print(f"Required roles: {decorator.required_roles}")
```

---

## Choice Tree: Which Layer?

```
Error in test?
├── Yes: Is it a unit test or integration test?
│   ├── Unit: Is dependency injected correctly? → Check Service/Repository layer
│   └── Integration: Does it involve DB, middleware, or templates? → Use checklist below
├── No: Error in production/running app?
│   └── Continue to Step 2 questions

Error message mentions:
├── "QuerySet", "migration", "schema": → ORM Layer
├── "TemplateError", "undefined", "filter": → Templates Layer
├── "KeyError" with context: → Middleware Layer
├── "AttributeError" with None: → Check current layer, trace upward
├── "asyncio", "coroutine", "await": → Async Layer
├── "tenant", "schema isolation": → Multi-Tenancy Layer
├── "token", "unauthorized", "permission": → Auth Layer
└── "Not sure": → Add logging, trace execution, repeat checklist

Error involves multiple layers?
├── Yes: Start with lowest layer (ORM/DB), work upward
└── No: Focus on single layer above
```

---

## Isolation Test Script

When you've narrowed to a layer, create a minimal test to verify:

```python
# tests/debug/test_isolated_<layer>.py

import pytest
from eden.db import Database
from eden.middleware import AuthMiddleware
from eden.templates import render

@pytest.mark.asyncio
async def test_orm_isolation():
    """Test ORM layer in isolation"""
    db = Database(":memory:")
    
    # Create table
    await db.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT
        )
    """)
    
    # Test query
    await db.execute("INSERT INTO users (name) VALUES (?)", ["Alice"])
    result = await db.execute("SELECT * FROM users")
    
    assert len(result) == 1
    assert result[0]["name"] == "Alice"

def test_middleware_isolation(app):
    """Test middleware in isolation"""
    # Create minimal request
    request = Request("GET", "/")
    request.headers["Authorization"] = "Bearer token"
    
    # Apply middleware
    middleware = AuthMiddleware(app)
    response = middleware(request)
    
    # Verify request was authorized
    assert request.user is not None

def test_template_isolation():
    """Test template in isolation"""
    context = {"user": "Alice", "items": [1, 2, 3]}
    result = render("template.html", context)
    
    assert "Alice" in result
    assert "<li>1</li>" in result
```

---

## Next Steps

Once you've identified the layer:
1. Review this checklist's diagnostics for that layer
2. Add logging/print statements to trace execution
3. Create isolated test (see above)
4. Move to **Inspect** phase in main SKILL.md
