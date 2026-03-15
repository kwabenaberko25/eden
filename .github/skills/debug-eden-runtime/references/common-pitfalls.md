# Common Pitfalls: Known Eden Framework Error Patterns

This guide documents common mistakes found during Eden Framework development and how to avoid or diagnose them.

---

## 🔴 Critical Pitfalls (High Impact)

### 1. Missing Await on Async Functions

**Symptom**: Function returns None or coroutine object, no execution happens

**Example**:
```python
# ❌ WRONG - coroutine created but not executed
result = db.query(User).filter(id=1)  # Returns coroutine, doesn't execute

# ✅ CORRECT - actually executes
result = await db.query(User).filter(id=1)
```

**Root Cause**: Python async functions return coroutines until awaited. If you forget `await`, the code compiles but doesn't run.

**Diagnosis**:
- Check for `<coroutine object>` in error or logs
- Look for any function call without `await` that returns a coroutine
- Use type checker: `mypy eden/ --ignore-missing-imports`

**Prevention**:
- Enable IDE warnings for unawaited coroutines
- Use `pytest-asyncio` plugin to catch missing awaits in tests
- Code review to find missing `await`

---

### 2. Missing Tenant Context in Multi-Tenant Query

**Symptom**: Query returns data from wrong tenant, or error: `KeyError: 'tenant_id'`

**Example**:
```python
# ❌ WRONG - query not filtered by tenant
users = await User.objects.all()  # Gets ALL users across tenants!

# ✅ CORRECT - filtered by current tenant
users = await User.objects.filter(tenant=request.tenant).all()
```

**Root Cause**: Multi-tenant apps must explicitly scope queries. Eden requires explicit filtering.

**Diagnosis**:
- Check logs: Is tenant ID logged before query?
- Add assertion: `assert request.tenant is not None`
- Compare generated SQL: Does it include tenant_id filter?

**Prevention**:
- Create helper method: `User.for_tenant(tenant)`
- Add QuerySet method that auto-filters by tenant
- Review queries in code review specifically for tenant filtering

---

### 3. Context Var Not Set in Async Context

**Symptom**: `ContextVar value not found` error, or None returned unexpectedly

**Example**:
```python
# ❌ WRONG - context not available here
def sync_function():
    user = request_context.get()  # Fails: running outside async context
    return user

# ✅ CORRECT - inside async or request handler
@app.get("/user")
async def get_user():
    user = request_context.get()  # Works: inside request context
    return user
```

**Root Cause**: Python ContextVar only works in async context. Sync code can't access request context.

**Diagnosis**:
- Check stack trace: Is error in sync or async function?
- Verify middleware sets context: `set_current_tenant(tenant_id)`
- Log context at start of request handler

**Prevention**:
- Keep all request-dependent code async
- Middleware should set context before calling handler
- Add test that explicitly checks context var is set

---

### 4. Middleware Applied But Not Executing

**Symptom**: Middleware setup looks correct but doesn't run, request fails

**Example**:
```python
# ❌ WRONG - middleware registered but method signature wrong
@app.middleware
async def my_middleware(request, call_next):
    return call_next(request)  # Not awaited!

# ✅ CORRECT - proper middleware pattern
@app.middleware
async def my_middleware(request, call_next):
    response = await call_next(request)
    return response
```

**Root Cause**: Middleware must properly return coroutine via `await`; improper signature or missing await breaks pipeline.

**Diagnosis**:
- Check middleware order in app startup logs
- Verify middleware method is actually async
- Test middleware in isolation with minimal request

**Prevention**:
- Create middleware test fixture
- Review middleware chain in tests
- Use middleware factory pattern for testability

---

## 🟡 Common Pitfalls (Medium Impact)

### 5. Type Mismatch in Query Filter

**Symptom**: `TypeError` or silent query failure

**Example**:
```python
# ❌ WRONG - StringField filtered with integer
user = await User.objects.filter(email=12345).get()  # Type mismatch

# ✅ CORRECT - correct type
user = await User.objects.filter(email="user@example.com").get()
```

**Root Cause**: No type coercion at query layer. StringField expects string, not integer.

**Diagnosis**:
- Check field type: `User._meta.get_field("email").get_type()`
- Print actual value being filtered
- Test with matching type

**Prevention**:
- Enable strict type checking: `mypy eden/`
- Add QuerySet validation for common fields
- Create helper for safe filters

---

### 6. N+1 Query Problem

**Symptom**: Slow queries, many redundant SQL calls

**Example**:
```python
# ❌ WRONG - loop executes query for each item
users = await User.objects.all()
for user in users:
    posts = await user.posts.all()  # N queries! (N = number of users)

# ✅ CORRECT - prefetch related objects
users = await User.objects.prefetch_related("posts").all()
for user in users:
    posts = user.posts  # Already loaded
```

**Root Cause**: Lazy loading relationships executes query for each access.

**Diagnosis**:
- Enable query logging: `logger.level = DEBUG`
- Count SQL executions in logs
- Use profiling: `pytest-benchmark` with query counting

**Prevention**:
- Use `select_related()` for ForeignKey
- Use `prefetch_related()` for ReverseFK and ManyToMany
- Test with AssertNumQueries fixture

---

### 7. Template Directive Undefined

**Symptom**: `Template error: Unknown directive 'my_directive'`

**Example**:
```html
<!-- ❌ WRONG - directive not registered -->
<div {% my_custom_directive %}>Content</div>

<!-- ✅ CORRECT - directive loaded in template engine -->
<div {% custom_registered_directive %}>Content</div>
```

**Root Cause**: Custom directives must be registered before template rendering.

**Diagnosis**:
- Check `eden/templates/directives/` for directive definition
- Verify directive is imported in `eden/templates/__init__.py`
- Test rendering with minimal template

**Prevention**:
- Create directive registry test
- Document required directives in template docs
- Test all templates at startup

---

### 8. Foreign Key Constraint Violation

**Symptom**: `IntegrityError: Foreign key constraint failed`

**Example**:
```python
# ❌ WRONG - creating Post for non-existent User
post = Post(user_id=9999, title="Test")
await db.save(post)  # Fails: User 9999 doesn't exist

# ✅ CORRECT - verify parent exists first
user = await User.objects.get(id=user_id)
if user:
    post = Post(user=user, title="Test")
    await db.save(post)
```

**Root Cause**: Database constraint enforces referential integrity. Parent must exist.

**Diagnosis**:
- Check error message for which foreign key fails
- Query parent table directly
- Verify transaction order

**Prevention**:
- Validate foreign key before save
- Create parent in test setup
- Add CASCADE or SET_NULL policies as needed

---

## 🟠 Architectural Pitfalls

### 9. Dependency Injection Not Used

**Symptom**: Hard to test, tight coupling, configuration issues

**Example**:
```python
# ❌ WRONG - hardcoded, not injectable
class UserService:
    def __init__(self):
        self.db = Database()  # Always uses production DB
        self.logger = logging.getLogger(__name__)  # No control

# ✅ CORRECT - dependencies injected
class UserService:
    def __init__(self, db: Database, logger: Logger):
        self.db = db
        self.logger = logger
```

**Root Cause**: Hardcoded dependencies are inflexible; injection enables testing and configuration.

**Diagnosis**:
- Hard to mock in tests? → Missing injection
- Config not working? → Check if value is used or hardcoded
- Can't swap implementations? → Not injected

**Prevention**:
- Create service registry/container
- Use factory functions for complex objects
- Add type hints to constructor

---

### 10. Transaction Scope Incorrect

**Symptom**: Data inconsistency, partial saves, race conditions

**Example**:
```python
# ❌ WRONG - two separate transactions
user.credits -= 10
await db.save(user)  # Transaction 1 commits

transaction.amount = 10
await db.save(transaction)  # Transaction 2 commits - fails, credits already deducted!

# ✅ CORRECT - single transaction
async with db.transaction():
    user.credits -= 10
    await db.save(user)
    
    transaction.amount = 10
    await db.save(transaction)  # All-or-nothing
```

**Root Cause**: Multi-step operations need atomic transaction. Separate saves can fail midway.

**Diagnosis**:
- Check error logs for "transaction" or "rollback"
- Verify related saves happen in one transaction
- Test by causing failure midway

**Prevention**:
- Use transaction context manager for multi-step operations
- Document transaction requirements in service docs
- Test with forced failures

---

## 🔵 Data & State Pitfalls

### 11. Datetime Without Timezone

**Symptom**: Wrong timestamps, time display issues in UI

**Example**:
```python
# ❌ WRONG - naive datetime (no timezone)
import datetime
now = datetime.datetime.now()  # No timezone info

# ✅ CORRECT - timezone-aware
import datetime
now = datetime.datetime.now(tz=datetime.timezone.utc)
```

**Root Cause**: Different timezones cause confusion; always use UTC.

**Diagnosis**:
- Check field definition: `created_at = DateTimeField(...)`
- Log timestamp value and check for `tzinfo`
- Compare UI display with database value

**Prevention**:
- Define constant: `UTC = timezone.utc`
- Create helper: `def now(): return datetime.now(UTC)`
- Add assertion in tests: `assert obj.created_at.tzinfo is not None`

---

### 12. Mutable Default Values

**Symptom**: Unexpected state sharing, test interference

**Example**:
```python
# ❌ WRONG - mutable default shared across instances
class User:
    def __init__(self, name, tags=[]):
        self.name = name
        self.tags = tags  # Same list for all Users!

# ✅ CORRECT - create new list for each instance
class User:
    def __init__(self, name, tags=None):
        self.name = name
        self.tags = tags or []  # New list per instance
```

**Root Cause**: Python creates default values once at definition time; they're shared.

**Diagnosis**:
- Log object IDs: `print(id(obj.tags))`
- Check if modifying one object affects another
- Look for `= []` or `= {}` in __init__

**Prevention**:
- Always use `None` as default for mutable types
- Create fresh instance in __init__: `self.tags = tags or []`
- Code review to catch mutable defaults

---

## 📋 Debugging Checklist

When you hit an error:

- [ ] **Reproduce**: Can I repeat it consistently?
- [ ] **Isolate**: Which layer/function?
- [ ] **Check Basics**: Missing await, wrong type, context not set?
- [ ] **Common Pitfalls**: Matches pattern #1-12 above?
- [ ] **Add Logging**: Print state before/after
- [ ] **Fix**: Apply minimal targeted fix
- [ ] **Verify**: Test passes, no regressions

---

## Quick Reference: By Error Message

| Error | Likely Pitfall | Check |
|-------|---|---|
| `TypeError: 'coroutine' object is not ...` | #1: Missing await | Add `await` |
| `KeyError: 'tenant_id'` | #2: Missing tenant filter | Check `request.tenant` |
| `ContextVar value not found` | #3: Wrong context | Check async context |
| `Unknown directive` | #7: Template not registered | Check directives list |
| `IntegrityError: Foreign key` | #8: Parent not exists | Verify parent first |
| `AttributeError: 'NoneType'` | #3 or #2: Context not set | Check context vars |
| `TypeError: expected str, got int` | #5: Type mismatch | Verify types |
| `Slow query` | #6: N+1 problem | Use prefetch_related |

---

## Prevention Strategy

1. **Per Layer**: Review common pitfalls in your layer (ORM, middleware, etc.)
2. **Per Feature**: Add tests that cover pitfall scenarios
3. **Per PR**: Code review checklist includes common pitfalls
4. **Per Deployment**: Enable debug logging and monitoring

---

## Related Documentation

- [Isolation Checklist](./isolation-checklist.md) — Layer-specific diagnostics
- [Eden Layers](./eden-layers.md) — Architecture reference
- Main [SKILL.md](../SKILL.md) — Full debugging workflow
