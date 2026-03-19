# 💉 Dependency Injection: Async Resource Management

**Build decoupled, testable, and high-performance applications with Eden's integrated Dependency Injection (DI) system. Inspired by FastAPI and designed for async-first enterprise architectures, Eden manages your resources from request to cleanup with zero friction.**

---

## 🧠 Conceptual Overview

Eden's DI system uses a **Provider Pattern**. Whenever a route handler or service requires an object (e.g., a database session or an authenticated user), the DI system resolves that object, caches it for the duration of the request, and cleans up any resources when the request finishes.

### The Lifecycle of a Dependency

```mermaid
graph TD
    A["Public Request"] --> B["DI Manager: Resolve Route Handler"]
    B --> C["Step 1: Parse Dependencies tree"]
    C --> D["Step 2: Initialize Provider (Setup")]
    D --> E["Step 3: Execute Handler (Business Logic")]
    E --> F["Step 4: Cleanup Provider (Teardown")]
    F --> G["Response Returned"]
```

---

## 🚀 The Core: `Depends()`

The `Depends()` marker tells Eden how to resolve a parameter.

### Simple Dependency
```python
from eden.dependencies import Depends

async def get_db_session():
    """Provider: Yields an active DB session with auto-cleanup."""
    session = await get_session()
    try:
        yield session
    finally:
        await session.close()

@app.get("/users")
async def list_users(session=Depends(get_db_session)):
    # session is automatically resolved and provided!
    users = await User.query(session).all()
    return users
```

---

## 🏗️ Typed Injections

Eden automatically resolves several common parameters based on their type hint or name without needing an explicit `Depends()`.

| Type Hint / Name | Description |
| :--- | :--- |
| `request` | Returns the current `Request` object. |
| `state` | Returns the `app.state` configuration object. |
| `session` | Returns a scoped `AsyncSession` (automatically managed). |
| `app` | Returns the `Eden` application instance. |

---

## ⚡ Dependency Patterns

### 1. Generators (Cleanup Pattern)
Use `yield` to perform setup before the handler runs and cleanup (teardown) after it finishes—critically useful for file handles or DB transactions.

```python
async def get_temp_file():
    f = open("temp.log", "w")
    try:
        yield f
    finally:
        f.close() # Teardown happens automatically after response
```

### 2. Nested Dependencies (Tree Resolution)
Dependencies can themselves depend on other dependencies. Eden resolves the entire tree recursively and caches results per request.

```python
@app.get("/me")
async def show_me(user=Depends(get_current_user)):
    # get_current_user depends on get_db_session
    # both are resolved and cached for this request!
    return user
```

---

## 🧪 Testing & Prototyping: Overrides

One of the most powerful features of Eden's DI is the ability to swap implementations during testing without modifying your business logic.

```python
from eden.testing import TestClient

# 1. Define your mock dependency
async def use_mock_db():
    return MockDatabase()

# 2. Patch your application globally for tests
app.dependency_overrides[get_db_session] = use_mock_db

# 3. All routes now use the Mock instead of the real DB!
client = TestClient(app)
```

---

## 🎨 Advanced: Sub-Graph Resolution

By default, dependencies are **cached per request**. If multiple sub-dependencies require the same database session, the session provider is called only **once**, and the instance is shared across the entire resolution graph.

---

## 💡 Best Practices

1.  **Use Generators for I/O**: Always use `yield` when dealing with files or multi-step transactions to ensure reliable cleanup.
2.  **Keep it Simple**: Don't build deeply nested dependency trees (more than 3 levels). If a dependency is too complex, refactor it into a Service class.
3.  **Type-Safe Injections**: Always use type hints for injected parameters. This allows your IDE to provide full autocomplete for the resolved objects.
4.  **Avoid Global Overrides in Production**: Only use `dependency_overrides` in test environments to prevent unpredictable production behavior.

---

**Next Steps**: [Advanced Templating & Directives](templating.md)
