# Eden Framework Layers Overview

This reference explains the key layers and subsystems to help you isolate errors.

## Core Layers

### 1. **ORM & Database Layer** (`eden/db/`)
- **Components**: Model definitions, QuerySet, migrations, schema management
- **Common Errors**:
  - `AttributeError: 'NoneType' object has no attribute 'id'` → Query returned None
  - `IntegrityError` → Unique constraint violated, nullable field required
  - `OperationalError` → Connection issues, schema mismatch
  - Tenant data leaking across tenants → Schema isolation not enforced

**Diagnostics**:
```python
# Check if query is actually executing
result = User.all().debug()  # Logs SQL
print(result.query)           # View generated SQL
```

### 2. **Middleware & Request Handling** (`eden/http/` + `eden/middleware/`)
- **Components**: CSRF, auth, session binding, headers parsing, context vars
- **Common Errors**:
  - `CSRF token mismatch` → Token not in session or form
  - `User not authenticated` → Auth middleware not running or misconfigured
  - `KeyError: 'current_user'` → Request context not set up
  - `403 Forbidden` → Permission check before view execution

**Diagnostics**:
- Check middleware ordering in app setup
- Verify context vars are set: `get_current_user()`, `get_current_tenant_id()`
- Check headers are passed to test client

### 3. **Template Engine** (`eden/templates/`)
- **Components**: Directive parsing (@if, @for, @csrf), context rendering
- **Common Errors**:
  - `Directive syntax error` → Nested blocks, special characters
  - `NameError: 'variable_name' is not defined` → Context missing or misnamed
  - `CSRF token is None` → Token not in request.session
  - Wrong line numbers in error messages → Regex preprocessing issue

**Diagnostics**:
- Check protected_blocks logic for edge cases
- Verify context dict has all required keys
- Test template in isolation

### 4. **Task/Scheduler Layer** (`eden/tasks/`)
- **Components**: Periodic tasks, background jobs, event publishing
- **Common Errors**:
  - `Task never runs` → Scheduler not started or cron expression wrong
  - `Task fails silently` → Exception caught but not logged
  - `Context lost in async` → Context vars not copied to task context

**Diagnostics**:
- Check app startup hooks for PeriodicTask.start()
- Verify task logs for exceptions
- Test task directly: `await my_task.run()`

### 5. **Multi-Tenancy & Context** (`eden/tenancy/` + context vars)
- **Components**: TenantMiddleware, tenant context, schema isolation
- **Common Errors**:
  - `Data from wrong tenant returned` → Query not filtered by tenant
  - `KeyError: 'tenant_id'` → Middleware not extracting tenant ID
  - `Schema 'tenant_x' does not exist` → Migration not run, wrong schema name

**Diagnostics**:
```python
# Check current tenant
from eden.tenancy import get_current_tenant_id
print(get_current_tenant_id())  # Should be set in request middleware

# Check query filtering
User.all().query  # Should have WHERE tenant_id = ?
```

### 6. **Component & WebSocket Layer** (`eden/components/`, `eden/websocket/`)
- **Components**: Component rendering, real-time updates, connection management
- **Common Errors**:
  - `TypeError: get_context_data() missing arguments` → Component data not passed
  - `WebSocket connection rejected` → Auth not enforced, no user context
  - `Message lost` → Broadcasting without tenant isolation

**Diagnostics**:
- Test component in isolation with mocked dependencies
- Check WebSocket auth flow in tests
- Verify message broadcast includes correct tenant/user scopes

---

## Cross-Layer Issues

### Async/Context Issues
- **Problem**: Context vars (current_user, current_tenant) lost in async tasks
- **Diagnosis**: Check if context copied to task context, await used correctly
- **Solution**: Use `copy_context()` when spawning tasks

### Circular Dependencies
- **Problem**: Module A imports B, B imports A → ImportError
- **Diagnosis**: Trace all imports, look for `from module import ...` at module level
- **Solution**: Move import inside function, use TYPE_CHECKING, or restructure

### Transaction Handling
- **Problem**: Partial data committed on error
- **Diagnosis**: Check if using `async with db.transaction():`
- **Solution**: Wrap multi-step writes in explicit transaction

---

## Debugging Workflow by Layer

| Layer | Check First | Check Second | Check Third |
|-------|------------|--------------|------------|
| **ORM** | Query output (SQL) | Data types returned | Transaction state |
| **Middleware** | Middleware ordering | Context vars set | Headers/session |
| **Templates** | Directive syntax | Context dict keys | protected_blocks |
| **Tasks** | Task execution called? | Task exception logs | Context copied? |
| **Multi-Tenant** | Tenant ID extracted? | Query filtered? | Schema exists? |
| **Components** | Context data passed? | Component rendering | JS integration |

