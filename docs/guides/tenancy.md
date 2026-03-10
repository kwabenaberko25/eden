# Multi-Tenancy 🏢

Eden is built from the ground up to support SaaS applications. Its multi-tenancy system provides row-level isolation that is transparent to the developer.

## Core Concepts

In Eden, a **Tenant** represents a silo of data (e.g., an Organization, a Team, or a Client).

### 1. Enabling the Middleware
Multi-tenancy is activated globally in your `app.py`.

```python
app.add_middleware("tenancy")
```

### 2. The `TenantMixin`
Any model you want to isolate should inherit from `TenantMixin`.

```python
from eden.tenancy import TenantMixin
from eden.db import EdenModel, StringField

class Project(EdenModel, TenantMixin):
    name: Mapped[str] = StringField()
```

This adds a `tenant_id` column to your table automatically.

---

## Automatic Scoping 🎯

Once configured, Eden's ORM automatically filters all queries based on the current tenant in the request context.

```python
# No need to manually filter by tenant_id!
# This only returns projects belonging to the current user's tenant.
projects = await Project.all()
```

---

## Global (Shared) Data

If a model should be shared across all tenants (like standard Roles or system Settings), simply omit the `TenantMixin`.

```python
class SystemStatus(EdenModel):
    # Shared by everyone
    is_maintenance: Mapped[bool] = BoolField()
```

---

## Tenant Context Management

You can manually switch or verify the tenant context in background tasks or administration scripts.

```python
from eden.tenancy import set_current_tenant

async with set_current_tenant(org.id):
    # Everything inside this block is scoped to 'org.id'
    await Project.create(name="Scoped Project")

---

## Bypassing Isolation 🔑

In rare cases (like global analytics or superuser tools), you may need to query across all tenants.

```python
from eden.tenancy import ignore_tenant

async with ignore_tenant():
    # This query bypasses all row-level security
    all_projects = await Project.all()
```

---

## Schema-Based Isolation 🏗️

While Eden defaults to **Shared Database, Shared Schema** (row-level isolation), it also supports **Shared Database, Separate Schema** for higher isolation requirements.

Set `TENANCY_STRATEGY=schema` in your `.env` to enable schema switching based on the current tenant's `schema_name` field.
```

---

## Multi-Tenancy Drift Detection

Eden includes internal utilities to detect when queries might be missing a tenant scope, helping you maintain a secure, leak-proof SaaS.

---

**Next Steps**: [Internationalization](i18n.md)
