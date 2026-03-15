# Multi-Tenancy Security Enforcement Guide

## Overview

The Eden Framework implements a comprehensive, multi-layer tenant isolation system to ensure data belonging to one tenant cannot be accessed by another, even in the presence of developer mistakes or edge cases.

## Architecture

Tenant isolation is enforced at **four distinct layers**, each providing independent protection:

```
┌─ Request ──────────────────────────────────────────────────┐
│                                                             │
│  1. TenantMiddleware resolves tenant from request          │
│     ↓ Sets context var: set_current_tenant(tenant)         │
│                                                             │
│  2. QuerySet auto-filters by context                       │
│     ↓ Injects WHERE tenant_id = context.get_current()      │
│                                                             │
│  3. RawQuery validates tenant context                      │
│     ↓ Warns if raw SQL lacks tenant_id filter              │
│                                                             │
│  4. Database schema isolation (optional)                   │
│     ↓ Dedicated PostgreSQL schema per tenant                │
│     ↓ Isolation enforced at database level                 │
│                                                             │
└─ Response ────────────────────────────────────────────────┘
   Headers: X-Tenant-Enforced, X-Tenant-ID
```

---

## Layer 1: Query-Level Enforcement (Automatic)

**File**: `eden/tenancy/mixins.py` → `TenantMixin`

### What It Does

When a `Model` inherits from `TenantMixin`, all queries automatically filter by the current tenant from context.

```python
class Project(Model, TenantMixin):
    __tablename__ = "projects"
    name: str = f()
    # Automatically gets tenant_id: UUID = ForeignKey("eden_tenants.id")
```

### Mechanism

1. **`TenantMixin._base_select()`** is called by `QuerySet.__init__()`
2. Checks `get_current_tenant_id()` from context
3. If no context (empty UUID), returns `false()` → empty result set (fail-secure)
4. If context exists, injects `WHERE tenant_id = <context_id>`

### Usage

```python
# This automatically only returns projects for the current tenant
projects = await Project.all()

# This also auto-filters - cannot access another tenant's projects
project = await Project.get(project_id)

# Filters are combined WITH the tenant filter
results = await Project.filter(name="Backend").all()
# Becomes: WHERE tenant_id = <context_id> AND name = 'Backend'
```

### Fail-Secure Behavior

Without tenant context, **all queries return empty**:

```python
# In a background task or misconfigured middleware with no tenant context:
projects = await Project.all()  # Returns [] not all projects!
```

This prevents accidental loops that forget to set context from leaking data.

### Bypassing (For Admin Operations)

To query all tenants (e.g., admin dashboard):

```python
# Query directly with SQL bypassing the ORM:
from eden.db.raw_sql import RawQuery
results = await RawQuery.execute(
    "SELECT * FROM projects",
    _skip_tenant_check=True  # Explicit admin override
)
```

---

## Layer 2: Raw SQL Protection

**File**: `eden.db.raw_sql.py` → `RawQuery`, `raw_update()`

### What It Does

Validates that raw SQL queries respect tenant isolation when a tenant context is active.

### Mechanism

1. **`RawQuery._validate_tenant_isolation(sql, skip_check)`**
   - Checks if tenant context is active
   - If yes, analyzes SQL for `tenant_id` or `eden_tenants` references
   - For SELECT queries without tenant filter: **logs warning**
   - For other operations: allows (they're implicitly scoped)

2. **Implementation Note**: Currently **warns** for backward compatibility
   - Future: Will raise `TenantException` for strict enforcement
   - Developers must explicitly use `_skip_tenant_check=True` for privileged operations

### Usage

```python
from eden.db.raw_sql import RawQuery

# This warns if tenant context is active
result = await RawQuery.execute(
    "SELECT * FROM projects WHERE created_by = $1",
    [user_id]
)

# To explicitly allow (for admin):
result = await RawQuery.execute(
    "SELECT * FROM projects WHERE created_by = $1",
    [user_id],
    _skip_tenant_check=True
)

# raw_update also validates:
await raw_update(
    table="projects",
    values={"active": True},
    where="id = $1",
    where_params=[project_id]
)
```

### Why Raw SQL Needs Protection

Raw SQL can bypass the ORM's `TenantMixin` filtering entirely:

```python
# DANGEROUS - leaks cross-tenant data:
await RawQuery.execute("SELECT * FROM projects")

# SAFE - explicitly requests cross-tenant access:
await RawQuery.execute(
    "SELECT * FROM projects",
    _skip_tenant_check=True
)
```

---

## Layer 3: Schema Provisioning

**File**: `eden/tenancy/models.py` → `Tenant.provision_schema()`

### What It Does

For tenants using **dedicated PostgreSQL schemas**, safely provisions a new schema with all tables.

### Architecture

Some SaaS applications use one of two isolation strategies:

| Strategy | Schema | Pros | Cons |
|----------|--------|------|------|
| **Row-Level** | Shared | Simpler, single backup | Must verify filters |
| **Schema** | Per-tenant | Database enforces isolation | More schemas to manage |

### Usage

```python
# Create a tenant with dedicated schema
tenant = await Tenant.create(
    name="Acme Corp",
    slug="acme",
    schema_name="acme_schema"  # Triggers schema provisioning
)

# Provision the schema (create all tables inside it)
session = db.session()
await tenant.provision_schema(session)
await session.commit()
```

### Implementation Details

```python
async def provision_schema(self, session: AsyncSession):
    """
    1. Sanitizes schema name (alphanumeric + underscore)
    2. Creates schema: CREATE SCHEMA IF NOT EXISTS <name>
    3. Saves original search_path
    4. Sets search_path to new schema
    5. Runs Model.metadata.create_all() → creates tables in schema
    6. Resets search_path to original (CRITICAL for connection pool)
    """
```

### Connection Pool Safety

**Critical**: After provisioning, the method **always resets `search_path` to public**:

```python
finally:
    # CRITICAL: Connection pool leak prevention
    await session.execute(text(f"SET search_path TO {original_schema}"))
```

Why? If a connection with `SET search_path TO tenant_schema` is returned to the pool, the next connection using it will inherit the wrong schema, **bypassing isolation**.

---

## Layer 4: Middleware Enforcement

**File**: `eden/tenancy/middleware.py` → `TenantMiddleware`

### What It Does

1. Resolves tenant from request (subdomain, header, session, path)
2. Sets tenant context for the request lifetime
3. Switches database schema if tenant uses dedicated schema
4. Adds response headers for verification
5. Resets context and schema after response

### Strategies

```python
# Strategy 1: Subdomain-based (acme.myapp.com → acme tenant)
app.add_middleware("tenant", strategy="subdomain", base_domain="myapp.com")

# Strategy 2: Header-based (X-Tenant-ID: <slug or UUID>)
app.add_middleware("tenant", strategy="header", header_name="X-Tenant-ID")

# Strategy 3: Session-based
app.add_middleware("tenant", strategy="session", session_key="_tenant_id")

# Strategy 4: URL path-based (/t/acme/...)
app.add_middleware("tenant", strategy="path")
```

### Response Headers

All responses include enforcement headers when a tenant is active:

```
X-Tenant-Enforced: true
X-Tenant-ID: <uuid>
```

These allow clients to verify tenant isolation was enforced.

### Schema Switching

For dedicated-schema tenants:

```python
# Middleware automatically:
1. Detects tenant.schema_name
2. Calls: db_manager.set_schema(session, "tenant_schema")
3. Handler executes with that schema set
4. Finally block resets: db_manager.set_schema(session, "public")
```

### Error Recovery

Even if the handler raises an error, schema is still reset:

```python
try:
    response = await call_next(request)  # May raise
except Exception:
    # Re-raise, but finally block still runs
    raise
finally:
    reset_current_tenant(token)
    # Schema reset happens here even on error
```

---

## Security Best Practices

### ✅ DO

- Use `TenantMixin` on all customer-facing models
- Let QuerySet auto-filter (don't write custom tenant filters)
- Use `_skip_tenant_check=True` explicitly for admin operations
- Set tenant context in middleware (don't skip)
- Use response headers to verify enforcement

### ❌ DON'T

- Write raw SQL without tenant filtering (`_skip_tenant_check=False` by default)
- Skip TenantMiddleware
- Assume background tasks inherit request context (they don't)
- Hardcode schema names (use `schema_name` field)
- Query without active tenant context in handlers

### ⚠️ Edge Cases

**Background Tasks**: No request context, tenants must be set explicitly

```python
from eden.tenancy.context import set_current_tenant

@app.task("process_billing")
async def process_billing():
    for tenant in await Tenant.filter(is_active=True).all():
        token = set_current_tenant(tenant)
        try:
            # Now queries are scoped to this tenant
            projects = await Project.all()
            # ... process
        finally:
            reset_current_tenant(token)
```

**Cross-Tenant Operations**: Use raw SQL with explicit flag

```python
# Migrate project from one tenant to another
await raw_update(
    table="projects",
    values={"tenant_id": new_tenant_id},
    where="id = $1",
    where_params=[project_id],
    _skip_tenant_check=True  # Explicit admin override
)
```

**Admin Dashboards**: Query all data with skip flag

```python
from eden.db.raw_sql import RawQuery

# Show all tenants' projects
results = await RawQuery.execute(
    "SELECT * FROM projects ORDER BY tenant_id, name",
    _skip_tenant_check=True  # Explicit admin operation
)
```

---

## Testing Tenant Isolation

### Test Case: Verify Cross-Tenant Access Prevention

```python
@pytest.mark.asyncio
async def test_cross_tenant_prevention(tenant_a, tenant_b):
    # Create in Tenant A
    token_a = set_current_tenant(tenant_a)
    try:
        proj = await Project.create(name="Secret")
    finally:
        reset_current_tenant(token_a)
    
    # Try to access as Tenant B
    token_b = set_current_tenant(tenant_b)
    try:
        # Should return None (not found) due to auto-filtering
        result = await Project.get(proj.id)
        assert result is None
    finally:
        reset_current_tenant(token_b)
```

### Running Tests

```bash
pytest tests/test_multitenant_security.py -v
```

---

## Troubleshooting

### ❌ Problem: All queries return empty

**Cause**: No tenant context set

**Solution**: 
```python
from eden.tenancy.context import set_current_tenant, get_current_tenant_id

assert get_current_tenant_id() is not None  # Check context

# If None, set it:
token = set_current_tenant(tenant)
try:
    # Now queries work
    projects = await Project.all()
finally:
    reset_current_tenant(token)
```

### ❌ Problem: Raw SQL leaks data from other tenants

**Cause**: Query executed without tenant filter and without `_skip_tenant_check=True`

**Solution**:
```python
# Option 1: Add tenant filter to SQL
result = await RawQuery.execute(
    "SELECT * FROM projects WHERE tenant_id = $1 AND ...",
    [get_current_tenant_id(), ...]
)

# Option 2: Explicit admin override
result = await RawQuery.execute(
    "SELECT * FROM projects WHERE ...",
    _skip_tenant_check=True
)
```

### ❌ Problem: Schema not switching for dedicated-schema tenant

**Cause**: Forgot to call `provision_schema()` or middleware not set up

**Solution**:
```python
# Provision schema after creating tenant
session = db.session()
await tenant.provision_schema(session)
await session.commit()

# Verify middleware is handling schema switching:
# Check middleware logs for "Failed to switch to tenant schema"
```

---

## References

- **Context Vars**: `eden/tenancy/context.py`
- **Middleware**: `eden/tenancy/middleware.py`
- **Query Filtering**: `eden/tenancy/mixins.py` + `eden/db/query.py`
- **Raw SQL Protection**: `eden/db/raw_sql.py`
- **Schema Provisioning**: `eden/tenancy/models.py`
- **Tests**: `tests/test_multitenant_security.py`
