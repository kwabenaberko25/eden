# Tenant Configuration & Setup 🏢

Comprehensive guide for configuring and deploying multi-tenant SaaS applications with Eden. Covers environment variables, database setup, tenant registration, and scaling strategies.

---

## Quick Start

### Minimal Setup

```python
# app.py
from eden import Eden
from eden.tenancy import TenantMiddleware, TenantMixin
from eden.orm import Model, f
from datetime import datetime

app = Eden(__name__)

# 1. Enable tenancy
app.add_middleware(
    TenantMiddleware,
    strategy="header",           # Resolve from X-Tenant-ID header
    header_name="X-Tenant-ID"
)

# 2. Define tenant model
class Tenant(Model):
    __tablename__ = "tenants"
    __table_args__ = {"schema": "public"}  # Shared schema
    
    id = f(int, primary_key=True)
    name = f(str, max_length=100)
    slug = f(str, max_length=50, unique=True)
    created_at = f(datetime, default=datetime.now)

# 3. Define tenant-scoped models
class Project(TenantMixin, Model):
    __tablename__ = "projects"
    
    id = f(int, primary_key=True)
    name = f(str)
    # tenant_id automatically added by TenantMixin

# 4. Use in routes
@app.get("/projects")
async def list_projects(request):
    # Automatically scoped to current tenant
    projects = await Project.all()
    return {"projects": [p.dict() for p in projects]}

# 5. Register app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## Configuration

### Environment Variables

```bash
# .env

# Tenancy strategy
TENANCY_STRATEGY=header              # header, subdomain, session, path

# Header-based resolution
TENANCY_HEADER_NAME=X-Tenant-ID     # Custom header name

# Subdomain-based resolution
TENANCY_BASE_DOMAIN=example.com     # For subdomain routing

# Database
DATABASE_URL=postgresql://localhost/eden_main
TENANCY_DB_STRATEGY=shared           # shared or separate

# Schema isolation (if using separate schemas)
TENANCY_AUTO_CREATE_SCHEMAS=true    # Create schema on tenant creation
```

### Programmatic Configuration

```python
from eden import Eden
from eden.tenancy import TenantMiddleware

app = Eden(__name__)

# Override environment variables
app.add_middleware(
    TenantMiddleware,
    strategy=os.getenv("TENANCY_STRATEGY", "header"),
    header_name=os.getenv("TENANCY_HEADER_NAME", "X-Tenant-ID"),
    base_domain=os.getenv("TENANCY_BASE_DOMAIN", ""),
    session_key=os.getenv("TENANCY_SESSION_KEY", "_tenant_id")
)
```

---

## Tenant Resolution Strategies

### 1. Header-Based (APIs, Mobile Apps)

```python
app.add_middleware(
    TenantMiddleware,
    strategy="header",
    header_name="X-Tenant-ID"
)

# Client code
response = requests.get(
    "https://api.example.com/projects",
    headers={"X-Tenant-ID": "tenant_123"}
)
```

**When to use:**
- ✅ Mobile apps / REST APIs
- ✅ Server-to-server communication
- ✅ Multiple app instances serving same domain
- ❌ Web browsers (can't easily set headers)

### 2. Subdomain-Based (SaaS Web Apps)

```python
app.add_middleware(
    TenantMiddleware,
    strategy="subdomain",
    base_domain="example.com"
)

# Users access: acme.example.com, contoso.example.com
# Middleware extracts "acme", "contoso" as tenant identifiers
```

**When to use:**
- ✅ Traditional SaaS web apps
- ✅ Each customer gets custom subdomain
- ✅ Branding/white-label scenarios
- ❌ Single-domain multi-tenant apps

### 3. Session-Based (Web Apps with Login)

```python
app.add_middleware("session")  # Enable sessions first
app.add_middleware(
    TenantMiddleware,
    strategy="session",
    session_key="_tenant_id"
)

# After login, set in session
@app.post("/login")
async def login(request):
    user = await authenticate(request)
    request.session["_tenant_id"] = user.tenant_id
    return {"success": True}
```

**When to use:**
- ✅ Web apps with user accounts
- ✅ User login determines tenant
- ✅ Single domain, multiple customers
- ❌ APIs without sessions

### 4. Path-Based (Multi-tenant on Path)

```python
app.add_middleware(
    TenantMiddleware,
    strategy="path"  # Extract from /tenant123/...
)

# Users access: example.com/tenant123/projects
#               example.com/tenant456/dashboard
```

**When to use:**
- ✅ URL-based tenant separation
- ✅ Easy development (localhost/tenant1)
- ✅ Single domain, many customers
- ❌ Prettier URLs desired

---

## Database Configuration

### Shared Database, Shared Schema (Default)

All tenants' data in one schema with `tenant_id` filtering:

```python
from eden import Eden
from eden.tenancy import TenantMixin
from eden.orm import Model, f

class Project(TenantMixin, Model):
    __tablename__ = "projects"
    
    id = f(int, primary_key=True)
    tenant_id = f(int)  # Added automatically by TenantMixin
    name = f(str)

# Table structure:
# projects
# ├── id
# ├── tenant_id  ← All queries auto-filtered by this
# └── name

# Setup
class Tenant(Model):
    __tablename__ = "tenants"
    __table_args__ = {"schema": "public"}
    
    id = f(int, primary_key=True)
    name = f(str)
```

**Pros:**
- Single database, single schema - simplest setup
- Easy migrations
- Flexible cross-tenant queries when needed

**Cons:**
- Queries must always filter by tenant_id
- Can accidentally leak data if filter forgotten

### Shared Database, Separate Schemas

Each tenant gets complete schema isolation:

```python
# .env
TENANCY_STRATEGY=schema
TENANCY_AUTO_CREATE_SCHEMAS=true

# Code
class Tenant(Model):
    __tablename__ = "tenants"
    __table_args__ = {"schema": "public"}  # In shared schema
    
    id = f(int, primary_key=True)
    name = f(str)
    schema_name = f(str, unique=True)  # Each tenant's schema

class Project(Model):
    __tablename__ = "projects"
    # No TenantMixin needed - schema provides isolation
    
    id = f(int, primary_key=True)
    name = f(str)
```

**Pros:**
- Complete physical isolation
- High security for regulated industries
- No risk of cross-tenant data leaks

**Cons:**
- Complex migrations (per schema)
- More overhead (multiple schema contexts)

See [Tenant Schema Switching](tenancy-postgres.md) for full details.

---

## Tenant Lifecycle

### Creating Tenants

```python
@app.post("/admin/tenants")
async def create_tenant(request):
    """Initialize new tenant."""
    body = await request.json()
    
    # 1. Create tenant record
    tenant = await Tenant.create(
        name=body["name"],
        slug=body["slug"],
        plan="standard"
    )
    
    # 2. If using schema isolation, create schema
    if os.getenv("TENANCY_STRATEGY") == "schema":
        db = await get_db(request)
        
        schema_name = f"tenant_{tenant.slug}"
        await db.execute(f"CREATE SCHEMA {schema_name}")
        
        # Update tenant record
        tenant.schema_name = schema_name
        await tenant.save()
        
        # 3. Run migrations in tenant schema
        # (See migrations section below)
    
    # 4. Seed initial data
    await seed_tenant(tenant)
    
    return {"tenant": tenant.dict()}

async def seed_tenant(tenant: Tenant):
    """Populate tenant with defaults."""
    # Switch to tenant context
    from eden.tenancy import set_current_tenant
    
    async with set_current_tenant(tenant.id):
        # Create default roles
        admin_role = await Role.create(
            name="Admin",
            permissions=["*"]
        )
        
        user_role = await Role.create(
            name="User",
            permissions=["read"]
        )
        
        # Create default settings
        await Settings.create(
            theme="light",
            language="en"
        )
        
        print(f"✓ Seeded tenant {tenant.name}")
```

### Updating Tenants

```python
@app.put("/admin/tenants/{id}")
async def update_tenant(id: int, request):
    """Update tenant configuration."""
    body = await request.json()
    
    tenant = await Tenant.get(id)
    tenant.name = body.get("name", tenant.name)
    tenant.plan = body.get("plan", tenant.plan)
    tenant.max_users = body.get("max_users")
    
    await tenant.save()
    
    return {"tenant": tenant.dict()}
```

### Deactivating Tenants

```python
@app.post("/admin/tenants/{id}/deactivate")
async def deactivate_tenant(id: int, request):
    """Deactivate tenant (soft delete)."""
    tenant = await Tenant.get(id)
    
    tenant.is_active = False
    tenant.deactivated_at = datetime.now()
    await tenant.save()
    
    # Reject requests for this tenant
    # (Implement in TenantMiddleware logic)
    
    return {"status": "deactivated"}

@app.post("/admin/tenants/{id}/delete")
async def delete_tenant(id: int, request):
    """Permanently delete tenant (with data)."""
    tenant = await Tenant.get(id)
    
    # If using schema isolation, drop schema
    if tenant.schema_name:
        db = await get_db(request)
        await db.execute(f"DROP SCHEMA {tenant.schema_name} CASCADE")
    
    # Delete all tenant data
    from eden.tenancy import set_current_tenant
    async with set_current_tenant(tenant.id):
        # Delete all tables in tenant's context
        await db.execute("DELETE FROM projects")
        await db.execute("DELETE FROM comments")
        # ... etc
    
    # Delete tenant record
    await tenant.delete()
    
    return {"status": "deleted"}
```

---

## User Invitation & Onboarding

```python
@app.post("/tenants/{tenant_id}/invite-users")
async def invite_users(tenant_id: int, request):
    """Send invites to new users."""
    body = await request.json()
    
    tenant = await Tenant.get(tenant_id)
    
    for email in body["emails"]:
        # Create invitation token
        token = secrets.token_urlsafe(32)
        
        invitation = await Invitation.create(
            tenant_id=tenant_id,
            email=email,
            token=token,
            expires_at=datetime.now() + timedelta(days=7)
        )
        
        # Send email with signup link
        await send_email(
            to=email,
            subject=f"Join {tenant.name} on Eden",
            body=f"Accept invite: https://example.com/join?token={token}"
        )
    
    return {"invited": len(body["emails"])}

@app.post("/join")
async def accept_invitation(request):
    """User accepts invitation and creates account."""
    body = await request.json()
    token = body["token"]
    
    # Find invitation
    invitation = await Invitation.find(token=token)
    if not invitation or invitation.is_expired():
        return {"error": "Invalid or expired invitation"}, 400
    
    # Create user
    from eden.tenancy import set_current_tenant
    
    async with set_current_tenant(invitation.tenant_id):
        user = await User.create(
            email=invitation.email,
            username=body["username"],
            password_hash=hash_password(body["password"]),
            role="user"
        )
    
    # Mark invitation as used
    invitation.used_at = datetime.now()
    invitation.user_id = user.id
    await invitation.save()
    
    return {"user": user.dict()}
```

---

## Billing & Plans

### Plan-Based Feature Limits

```python
# Models
class Tenant(Model):
    __tablename__ = "tenants"
    __table_args__ = {"schema": "public"}
    
    id = f(int, primary_key=True)
    name = f(str)
    plan = f(str)  # "free", "pro", "enterprise"
    max_users = f(int)
    max_projects = f(int)

# Plan definitions
PLANS = {
    "free": {
        "name": "Free",
        "price": 0,
        "max_users": 1,
        "max_projects": 5,
        "features": ["basic"]
    },
    "pro": {
        "name": "Pro",
        "price": 29,
        "max_users": 10,
        "max_projects": 100,
        "features": ["advanced", "api", "webhooks"]
    },
    "enterprise": {
        "name": "Enterprise",
        "price": "custom",
        "max_users": float('inf'),
        "max_projects": float('inf'),
        "features": ["all"]
    }
}

# Enforce limits
@app.post("/projects")
async def create_project(request):
    tenant = await get_current_tenant()
    body = await request.json()
    
    # Check project limit
    project_count = await Project.count()
    if project_count >= tenant.max_projects:
        return {
            "error": f"Max {tenant.max_projects} projects for {tenant.plan} plan"
        }, 402
    
    project = await Project.create(name=body["name"])
    return {"project": project.dict()}
```

### Subscription Webhooks

```python
@app.post("/webhooks/stripe")
async def stripe_webhook(request):
    """Handle Stripe subscription events."""
    
    # Verify webhook signature
    body = await request.body()
    signature = request.headers.get("Stripe-Signature")
    
    event = verify_stripe_signature(body, signature)
    
    if event["type"] == "customer.subscription.updated":
        # Update tenant plan
        customer_id = event["data"]["object"]["customer"]
        plan = event["data"]["object"]["metadata"]["plan"]
        
        tenant = await Tenant.find(stripe_customer_id=customer_id)
        tenant.plan = plan
        await tenant.save()
    
    elif event["type"] == "customer.subscription.deleted":
        # Downgrade to free
        tenant = await Tenant.find(stripe_customer_id=customer_id)
        tenant.plan = "free"
        await tenant.save()
    
    return {"received": True}
```

---

## Monitoring & Analytics

### Tenant Metrics

```python
@app.get("/admin/tenants/{id}/metrics")
async def tenant_metrics(id: int, request):
    """Get usage metrics for tenant."""
    
    from eden.tenancy import set_current_tenant
    
    tenant = await Tenant.get(id)
    
    async with set_current_tenant(tenant.id):
        user_count = await User.count()
        project_count = await Project.count()
        last_activity = await Activity.order_by("-created_at").first()
    
    return {
        "tenant": tenant.name,
        "plan": tenant.plan,
        "users": user_count,
        "projects": project_count,
        "last_activity": last_activity.created_at if last_activity else None,
        "created_at": tenant.created_at
    }

@app.get("/admin/metrics/all-tenants")
async def platform_metrics():
    """System-wide metrics."""
    
    tenants = await Tenant.count()
    active_tenants = await Tenant.filter(is_active=True).count()
    
    # Cross-tenant aggregation (reset tenant context)
    from eden.tenancy import set_current_tenant, reset_current_tenant
    
    token = set_current_tenant(None)
    try:
        total_projects = await Project.count()
        # This requires querying with tenant_id = ANY(...)
    finally:
        reset_current_tenant(token)
    
    return {
        "tenants": tenants,
        "active_tenants": active_tenants,
        "projects": total_projects
    }
```

---

## Migration Management

### Managing Multiple Tenants

```python
# alembic/versions/001_initial_schema.py

from alembic import op
import sqlalchemy as sa

def upgrade():
    # Create shared schema tables
    op.execute("CREATE TABLE IF NOT EXISTS tenants (id SERIAL PRIMARY KEY, name VARCHAR(100), created_at TIMESTAMP)")
    
    # Create tenant-scoped tables
    op.create_table(
        'projects',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    op.drop_table('projects')
    op.execute("DROP TABLE IF EXISTS tenants")
```

---

## API Reference

### TenantMiddleware

```python
TenantMiddleware(
    app,
    strategy: Literal["header", "subdomain", "session", "path"],
    header_name: str = "X-Tenant-ID",     # For "header" strategy
    base_domain: str = "",                 # For "subdomain" strategy
    session_key: str = "_tenant_id"        # For "session" strategy
)
```

### Tenant Context

```python
from eden.tenancy import set_current_tenant, get_current_tenant, reset_current_tenant

# Get current tenant
tenant = await get_current_tenant()

# Set tenant context
token = set_current_tenant(tenant)
try:
    # Operations scoped to tenant
finally:
    reset_current_tenant(token)
```

---

## Next Steps

- [Tenant Schema Switching](tenancy-postgres.md) - PostgreSQL isolation
- [Tenancy Fundamentals](tenancy.md) - Row-level isolation
- [Security & Multi-Tenancy](security.md#multi-tenancy-security) - Secure tenant access
- [Billing & Payments](../guides/payments.md) - Stripe integration
