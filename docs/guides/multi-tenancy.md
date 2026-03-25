# Multi-Tenancy Master Class: Scaling to 10k+ Tenants

Multi-tenancy is the heart of the Eden Framework. Unlike other frameworks that bolt on isolation as an afterthought, Eden’s storage architecture is built from the ground up to support **Hierarchical Tenancy**, **Policy-Based Isolation**, and **Infrastructure Sharding**.

---

## 🏗️ 1. Isolation Strategies: Row vs. Schema

Eden supports two primary strategies for isolating data. Choosing the right one depends on your compliance requirements and performance needs.

### Strategy A: Row-Level Isolation (The "Shared" Approach)
All tenants share the same database tables. Isolation is enforced via a mandatory `tenant_id` column.
- **Pros**: Simplest to manage, infinite tenant scaling, shared cache.
- **Cons**: Requires strict indexing on `tenant_id`, potential "noisy neighbor" issues if queries are unoptimized.
- **Used for**: Standard B2B SaaS, most applications.

### Strategy B: Schema-Level Isolation (The "Enterprise" Approach)
Each tenant gets its own PostgreSQL schema (within the same database).
- **Pros**: Stronger data isolation, easier backups for individual clients, custom extensions per tenant.
- **Cons**: Migrations take longer (must run once per schema), connection pooling can be trickier.
- **Used for**: High-compliance industries (FinTech, HealthTech), enterprise clients with "bring your own data" requirements.

---

## 🛡️ 2. The "Invisible" Firewall

Isolation in Eden is enforced at the **Database Driver** level using the `TenantMixin`. This ensures that even raw SQL queries or global filters respect the active tenant context.

```python
from eden.db import Model
from eden.tenancy import TenantMixin

class CustomerInquiry(TenantMixin, Model):
    __tablename__ = "inquiries"
    
    # Eden automatically adds and manages the 'tenant_id' column
    subject: str = f(StringField())
```

### How it Works:
1. **Middleware**: Resolves the tenant from the request (Subdomain, Header, or JWT).
2. **Registry**: Binds the `tenant_id` to the current `EdenContext` (Asynchronous context variable).
3. **Query Engine**: Every SQLAlchemy query is modified in-flight to include:
   ```sql
   WHERE tenant_id = '...'
   ```

---

## ⚡ 3. The "Super Admin" Bypass (`AcrossTenants`)

Sometimes, you *need* to break the firewall—to run global analytics, process system-wide billing, or perform emergency maintenance.

```python
from eden.tenancy import AcrossTenants

@app.get("/admin/global-revenue")
async def global_revenue(request):
    # Only Global Framework Admins should execute this
    async with AcrossTenants():
        total = await Invoice.sum("amount")
    return {"total": total}
```

> [!CAUTION]
> Using `AcrossTenants` is sensitive. Eden automatically logs all entries into this context to the Framework Audit trail for security compliance.

---

## 🧬 4. Multi-Tenant Lifecycle Management

Provisioning a new tenant isn't just about a DB row. It’s an orchestration workflow.

```python
async def onboard_customer(name: str, plan: str):
    # 1. Create the Tenant Identity
    tenant = await Tenant.create(name=name, plan=plan)
    
    # 2. Bootstrap Schema (if using Schema Isolation)
    if framework.config.TENANCY_STRATEGY == "schema":
        await tenant.bootstrap_schema()
        
    # 3. Use set_tenant_context to seed initial data
    async with set_tenant_context(tenant.id):
        await Folder.create(name="Home")
        await Setting.create(key="theme", value="dark")
```

---

## 💡 Performance Optimization

1. **Composite Indexing**: Eden automatically creates composite indexes on `(tenant_id, id)` and other common lookups to ensure `O(log n)` performance regardless of tenant count.
2. **Schema Caching**: For schema-level isolation, Eden caches the `search_path` per request to minimize overhead.
3. **Task Routing**: Background tasks in Eden inherit the `tenant_id` automatically, so `email.send_job.delay()` knows exactly which tenant context to use.

---

**Next: [Identity & RBAC Master Class](identity-rbac.md) →**
