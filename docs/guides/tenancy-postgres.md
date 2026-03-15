# Tenant Schema Switching in PostgreSQL 🗄️

For high-security multi-tenant applications, Eden supports **schema-based isolation** where each tenant has a completely separate PostgreSQL schema. This guide covers implementation, configuration, and deployment.

> **New to tenancy?** Start with [Tenancy Fundamentals](tenancy.md) first.  
> **Row-level isolation better for you?** That's the default - no configuration needed.

---

## Overview

### Row vs. Schema Isolation

**Row-Level Isolation** (default)
- ✅ Single database schema
- ✅ Simpler setup, fewer migrations
- ✅ Flexible: can query across tenants
- ❌ Every query must filter by `tenant_id`
- ❌ Must be fail-secure in code

**Schema-Level Isolation** (this guide)
- ✅ Complete database separation
- ✅ No filtering logic needed
- ✅ Highest compliance/security
- ✅ Schema-level access control
- ❌ More complex setup
- ❌ Migrations per schema needed

### When to Use Schema Isolation

**Use schema isolation if:**
- 🔒 Regulatory requirements (HIPAA, PCI, GDPR)
- 🔒 High-value multi-tenant SaaS
- 🔒 Customers demand data isolation
- 🔒 Audit compliance critical

**Use row-level if:**
- 💰 Cost-conscious (single schema cheaper)
- 🔄 Flexible tenant management
- 📊 Cross-tenant queries needed
- 🚀 Faster development

---

## PostgreSQL Architecture

### search_path Mechanism

PostgreSQL uses `search_path` to determine which schema to query:

```sql
-- Default search path
SHOW search_path;  
-- Output: "$user", public

-- Set schema for current session
SET search_path TO tenant_1;

-- Now all queries use tenant_1 schema
SELECT * FROM users;  -- Actually: SELECT * FROM tenant_1.users

-- Reset to public
SET search_path TO public;
```

### Multiple Schemas in One Database

```
┌─────────────────────────────────────────┐
│         PostgreSQL Database             │
├─────────────────────────────────────────┤
│                                         │
│  ┌──────────────┐  ┌──────────────┐   │
│  │ Tenant 1     │  │ Tenant 2     │   │
│  │ Schema       │  │ Schema       │   │
│  ├──────────────┤  ├──────────────┤   │
│  │ users        │  │ users        │   │
│  │ posts        │  │ posts        │   │
│  │ comments     │  │ comments     │   │
│  └──────────────┘  └──────────────┘   │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │ public (Shared)                  │  │
│  ├──────────────────────────────────┤  │
│  │ tenants (tenant registry)        │  │
│  │ migrations (version table)       │  │
│  └──────────────────────────────────┘  │
│                                         │
└─────────────────────────────────────────┘
```

---

## Implementation

### Eden's Schema Switching

Eden automatically manages schema switching in the request lifecycle:

```python
# In eden/tenancy/middleware.py (simplified)

async def dispatch(request, call_next):
    # 1. Resolve tenant from request
    tenant = await self._resolve_tenant(request)
    
    # 2. If tenant has schema_name, switch to it
    if tenant and tenant.schema_name:
        await db_manager.set_schema(db_session, tenant.schema_name)
    
    try:
        # 3. Handle request (all queries use this schema)
        response = await call_next(request)
        return response
    finally:
        # 4. CRITICAL: Reset to 'public' in finally block
        if tenant and tenant.schema_name:
            await db_manager.set_schema(db_session, "public")
```

### Why the Reset is Critical

PostgreSQL returns connections to a pool for reuse. If schema isn't reset:

```
Request 1 (Tenant A)
├─ SET search_path TO tenant_a
├─ Handle request
├─ Return connection to pool  ← Schema still tenant_a!
│
Request 2 (Tenant B) - Gets pooled connection
├─ Connection still on tenant_a schema
├─ Queries hit tenant_a data even though auth says tenant_b
├─ 🚨 DATA LEAK
```

Solution - **always reset in finally:**

```python
token = set_current_tenant(tenant)
schema_name = tenant.schema_name if tenant else None

try:
    # Handle request
    response = await call_next(request)
finally:
    # Always runs, even on exception
    if schema_name:
        await db_manager.set_schema(db_session, "public")
    reset_current_tenant(token)
```

---

## Configuration

### Step 1: Environment Variables

```bash
# .env
TENANCY_STRATEGY=schema              # Use schema-based isolation
TENANCY_HEADER_NAME=X-Tenant-ID     # Optional: header-based resolution
TENANCY_BASE_DOMAIN=example.com     # Optional: subdomain resolution
```

### Step 2: Tenant Model

Add `schema_name` field to track each tenant's schema:

```python
from eden import Eden
from eden.orm import Model, f

app = Eden(__name__)

class Tenant(Model):
    __tablename__ = "tenants"
    __table_args__ = {"schema": "public"}  # Shared schema
    
    id = f(int, primary_key=True)
    name = f(str, max_length=100, unique=True)
    schema_name = f(str, max_length=50, unique=True)  # ← NEW
    created_at = f(datetime, default=datetime.now)
    is_active = f(bool, default=True)
```

### Step 3: Tenant Registration

Create schemas when onboarding new tenant:

```python
@app.post("/admin/tenants/create")
async def create_tenant(request):
    data = await request.json()
    
    # 1. Create database schema
    tenant_schema = f"tenant_{data['slug']}"
    
    from eden.orm import get_db
    db = await get_db(request)
    await db.execute(f"CREATE SCHEMA {tenant_schema}")
    
    # 2. Run migrations in tenant schema
    # (See migrations section below)
    
    # 3. Register in public schema
    tenant = await Tenant.create(
        name=data['name'],
        schema_name=tenant_schema
    )
    
    return {"tenant_id": tenant.id}
```

### Step 4: TenantMiddleware Configuration

```python
from eden.tenancy import TenantMiddleware

app.add_middleware(
    TenantMiddleware,
    strategy="header",  # or "subdomain", "session", "path"
    header_name="X-Tenant-ID",  # If using header strategy
    base_domain="example.com",   # If using subdomain strategy
)
```

---

## Migration Strategy

### Alembic with Multiple Schemas

Create separate migration environments:

```bash
# Generate Alembic config
alembic init migrations

# Create multi-schema environment
# (See alembic/env.py setup below)
```

**alembic/env.py** (multi-schema setup):

```python
import os
from sqlalchemy import create_engine
from alembic import context
from logging.config import fileConfig

# List of all schemas (including tenant schemas)
SCHEMAS = ["public", "tenant_1", "tenant_2"]  # Auto-discover in production

def run_migrations_offline():
    """Offline migrations for all schemas."""
    for schema in SCHEMAS:
        config.set_main_option("sqlalchemy.url", f"postgresql://.../{schema}")
        
        with connectable.begin() as connection:
            context.configure(connection=connection)
            with context.begin_transaction():
                context.run_migrations()

def run_migrations_online():
    """Online migrations for all schemas."""
    for schema in SCHEMAS:
        connectable = create_engine("postgresql://...")
        
        with connectable.begin() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()
```

### Shared vs. Tenant-Specific Tables

**Shared (in public schema):**
- Tenant registry
- User accounts  
- Configuration

**Tenant-Specific (in each schema):**
- All application data
- Posts, comments, orders, etc.

```python
class User(Model):
    """Shared - in public schema."""
    __table_args__ = {"schema": "public"}
    
    id = f(int, primary_key=True)
    email = f(str, unique=True)
    password_hash = f(str)

class Post(Model):
    """Tenant-specific - auto-placed in tenant schema."""
    # Don't specify schema - use tenant context
    __tablename__ = "posts"
    
    id = f(int, primary_key=True)
    title = f(str)
    content = f(str)
    user_id = f(int)  # References User in public schema
```

### Seeding Tenant Schemas

Initialize with default data:

```python
async def seed_tenant_schema(schema_name: str):
    """Run seeding for new tenant."""
    from eden.orm import get_db
    
    db = await get_db()
    
    # Switch to tenant schema
    await db.set_schema(db.session, schema_name)
    
    try:
        # Create default roles
        admin_role = await Role.create(name="Admin", permissions=["*"])
        user_role = await Role.create(name="User", permissions=["read"])
        
        # Create settings
        settings = await Settings.create(
            theme="light",
            language="en"
        )
        
        print(f"✓ Seeded {schema_name}")
    finally:
        # Reset to public
        await db.set_schema(db.session, "public")
```

---

## Querying with Schema Isolation

### Automatic Schema Selection

```python
@app.get("/posts")
async def list_posts(request):
    # Tenant context automatically set by TenantMiddleware
    # All queries use the tenant's schema
    
    posts = await Post.all()  # Queries tenant schema only
    return {"posts": [p.dict() for p in posts]}
```

### Fail-Secure by Default

If tenant context is missing, queries return empty:

```python
# Without tenant set
posts = await Post.all()  # Returns [] (no data leak)
```

### Querying Shared Schema (Tenants Table)

```python
@app.get("/admin/tenants")
async def list_tenants(request):
    # Explicitly query public schema
    from eden.tenancy import explicitly_shared_schema
    
    with explicitly_shared_schema():
        tenants = await Tenant.all()
    
    return {"tenants": tenants}
```

### Cross-Schema Queries (Advanced)

Rarely needed but possible:

```python
# Get user from public schema while in tenant schema
from sqlalchemy import text

async def get_user_info(user_id: int):
    # Regular query (tenant schema)
    post_count = len(await Post.filter(user_id=user_id))
    
    # Cross-schema query (explicit public access)
    result = await get_db().execute(
        text("SELECT * FROM public.users WHERE id = :user_id"),
        {"user_id": user_id}
    )
    user = result.fetchone()
    
    return {
        "user": user,
        "post_count": post_count
    }
```

---

## Production Deployment

### Connection Pool Configuration

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    "postgresql://user:pass@localhost/eden_db",
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    # Reset search_path on every connection return
    pool_pre_ping=True,
)
```

### High-Traffic Optimization

For many tenants, consider:

1. **Connection pooling per schema:**
   ```python
   # Maintain separate pools per schema
   schema_pools = {
       "tenant_1": create_engine(...),
       "tenant_2": create_engine(...),
   }
   ```

2. **Schema caching:**
   ```python
   # Cache schema list to avoid repeated lookups
   @cache.cached(timeout=3600)
   async def get_all_schemas():
       return await Tenant.all()
   ```

3. **Lazy schema creation:**
   ```python
   # Create schemas on-demand, not upfront
   async def ensure_schema(tenant):
       if not await schema_exists(tenant.schema_name):
           await create_schema(tenant.schema_name)
   ```

### Monitoring & Debugging

```python
# Check current schema
@app.get("/debug/schema")
async def current_schema(request):
    from eden.orm import get_db
    db = await get_db(request)
    
    result = await db.execute("SHOW search_path")
    schema = result.scalar()
    
    return {"current_schema": schema, "tenant": request.state.tenant}

# List all schemas
@app.get("/admin/schemas")
async def list_schemas(request):
    from eden.orm import get_db
    db = await get_db(request)
    
    result = await db.execute("""
        SELECT schema_name FROM information_schema.schemata 
        WHERE schema_owner = current_user
    """)
    
    schemas = [row[0] for row in result]
    return {"schemas": schemas}
```

---

## Troubleshooting

### Problem: Data leak during concurrent requests

**Cause**: Schema not reset before connection reused  
**Solution**: Ensure finally block always runs:

```python
schema_name = tenant.schema_name
try:
    response = await call_next(request)
finally:
    if schema_name:
        await db.set_schema(db.session, "public")  # Always happens
```

### Problem: Slow queries with many schemas

**Cause**: Too many schema switches per request  
**Solution**: Cache schema context:

```python
# Don't switch multiple times
for item in items:
    async with switch_schema(item.schema):
        result = await query()  # Expensive

# Instead:
async with switch_schema(main_schema):
    for item in items:
        result = await query()  # Single switch
```

### Problem: Migration failed partway through

**Cause**: Alembic revisions not consistent across schemas  
**Solution**: Use alembic heads to verify:

```bash
alembic heads  # Should show single head
alembic current -schema tenant_1
alembic current -schema tenant_2
# Should all be at same revision
```

---

## API Reference

### TenantMiddleware

```python
TenantMiddleware(
    app,
    strategy: Literal["header", "subdomain", "session", "path"] = "header",
    header_name: str = "X-Tenant-ID",      # For "header" strategy
    base_domain: str = "",                  # For "subdomain" strategy  
    session_key: str = "_tenant_id"         # For "session" strategy
)
```

### Database Methods

```python
# Set schema for session
await db_manager.set_schema(db_session, "tenant_1")

# Get current schema
current = await db_manager.get_schema(db_session)

# Check if schema exists
exists = await db_manager.schema_exists("tenant_1")

# Create schema
await db_manager.create_schema("tenant_1")

# Drop schema
await db_manager.drop_schema("tenant_1")
```

---

## Comparison: Row vs Schema Isolation

| Feature | Row-Level | Schema-Level |
|---------|-----------|--------------|
| Setup complexity | Low | High |
| Query filtering | Code-level | Database-level |
| Cross-tenant queries | Possible | Requires explicit access |
| Compliance | Good | Excellent |
| Performance | Single schema | Per-schema overhead |
| Migration complexity | Single | Per-schema |
| Data isolation | Logical | Physical |

---

## Next Steps

- [Tenancy Fundamentals](tenancy.md) - Row-level isolation
- [Access Control](../guides/security.md#access-control) - Row-level security
- [Database Migrations](../guides/orm.md#migrations) - Alembic setup
- [Production Checklist](../guides/deployment.md) - Launch readiness
