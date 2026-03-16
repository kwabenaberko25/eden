# Multi-Tenancy: Schema-Based Isolation 🏗️

While Eden defaults to **Shared Database, Shared Schema** (row-level isolation via `tenant_id` columns), many enterprise SaaS applications require higher levels of data isolation. Eden provides built-in support for **Separate Schema** isolation using PostgreSQL's `search_path` mechanism.

---

## 🏛️ Isolation Strategies

| Strategy | Architecture | Privacy Level | Complexity |
| :--- | :--- | :--- | :--- |
| **Row-Level** | Shared Schema | Standard | Low (Default) |
| **Schema-Level** | Separate Schema per Tenant | High | Medium |
| **Db-Level** | Separate Database per Tenant | Absolute | High |

---

## 🚀 Enabling Schema Isolation

To switch Eden to schema-based isolation, update your configuration:

1. **Set Environment Variables**:
```bash
TENANCY_STRATEGY=schema
TENANCY_DEFAULT_SCHEMA=public
```

2. **Configure the Tenant Model**:
    Ensure your `Tenant` model has a `schema_name` field correctly populated.

---

## 🛠️ The Provisioning Workflow

When a new tenant signs up, you must provision their dedicated database schema. Eden provides a standard method on the `Tenant` model to automate this process including table creation.

```python
from eden.tenancy import Tenant
from eden.db import get_db

async def onboard_customer(name: str, slug: str):
    async with get_db() as session:
        # 1. Create the tenant record
        tenant = Tenant(
            name=name, 
            slug=slug, 
            schema_name=f"tenant_{slug}"
        )
        session.add(tenant)
        await session.commit()

        # 2. Provision the database schema
        # This creates the PG schema and runs all framework migrations/table creation
        await tenant.provision_schema(session)
        await session.commit()
    
    return tenant
```

### What `provision_schema()` does

1. **Sanitizes** the schema name (alphanumeric only).
2. Creates the schema: `CREATE SCHEMA IF NOT EXISTS {schema_name}`.
3. Temporarily sets the `search_path`: `SET search_path TO {schema_name}, public`.
4. Executes `Model.metadata.create_all()` to build all tables within that specific schema.
5. **Critically** resets the `search_path` back to `public` to prevent connection pool pollution.

---

## 🔄 Middleware Integration

When `TENANCY_STRATEGY=schema` is active, the `TenantMiddleware` performs the following on every request:

1.  **Resolves** the tenant from the URL/Header.
2.  **Acquires** a database connection.
3.  **Executes** `SET search_path TO {tenant_schema}, public` before your view handler runs.
4.  **Resets** the `search_path` when the request finishes and the connection returns to the pool.

This ensures that a simple `await User.all()` automatically targets the `users` table inside the current tenant's schema without you writing any custom SQL.

---

## 📦 Migrations in a Multi-Schema World

Migrations become more complex when data is spread across N schemas. Use Eden's CLI with the `---all-tenants` flag to apply migrations across your entire fleet.

```bash
# Apply a new migration to every tenant schema
eden migrate upgrade --all-tenants
```

---

## ⚠️ Critical Considerations

### 1. Connection Pooling
Schema switching happens at the connection level. If you manually acquire a connection and change the `search_path`, you **must** reset it before releasing the connection. Failure to do so will cause "Cross-Tenant Leaks" where the next request using that connection inherits the previous tenant's schema.

### 2. Migration Performance
With 1,000 tenants, running a migration means updating 1,000 schemas. Ensure your migration scripts are optimized and run during maintenance windows or background processes for large fleets.

### 3. Global vs. Scoped Tables
Tables for models that **do not** use `TenantMixin` should typically stay in the `public` schema. Eden's default `provision_schema` behavior creates ALL tables in the tenant schema; you may need to customize your `Metadata` strategy if you want a mix of global and scoped tables.

---

**Next Steps**: [SaaS Admin Panel](admin.md)
