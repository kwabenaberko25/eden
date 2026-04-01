# Identity & Access Control (RBAC): Hierarchical Security

Eden's Identity system provides a powerful framework for managing users, roles, and fine-grained permissions across your application.

By default, we support a **Tiered Admin Hierarchy** that plays seamlessly with our Multi-Tenancy system.

---

## 1. User Hierarchies (Tiered Admins)

Eden distinguishes between two primary types of administrators:

### The Global Framework Admin (The "Super Admin")

These users are **Tenantless** and have `is_superuser=True`. They are responsible for:

- Provisioning new tenants.
- Invoicing and system health.
- Cross-tenant reporting.

### The Single-Tenant Admin

These users are **Scoped** to a specific `tenant_id`. They can:

- Manage users *within* their tenant.
- Configure tenant-specific settings.
- NOT see data from any other tenant.

```python
from eden.auth import BaseUser
from eden.tenancy import TenantMixin

class User(BaseUser, TenantMixin):
    # This user is automatically isolated by tenant_id
    pass
```

---

## 2. Model-Level RBAC (Secure-by-Design)

Forget about checking permissions in every route handler. In Eden, you define your security rules **directly on your data models**.

Every `Model` in Eden can define an `__rbac__` attribute, which maps actions (e.g., `view`, `create`, `edit`, `delete`) to roles or permission rules.

```python
from eden.db import Model, StringField, AllowRoles, AllowOwner

class Document(Model, TenantMixin):
    title: str = StringField(max_length=200)
    
    __rbac__ = {
        "view": ["user", "admin"],
        "edit": ["admin", AllowOwner()],
        "delete": ["admin"],
    }
```

### Supported Rules

- **Role-Based**: `['admin', 'editor']` (String-based role names).
- **Dynamic**: `AllowOwner()` (Checks if `user_id` matches the current user).
- **Custom**: Create your own by inheriting from `PermissionRule`.

---

## 3. Applying Permissions in Queries

Eden's ORM automatically enforces these rules when you use the standard CRUD methods. If a user tries to access a record they don't have permission for, the ORM will:

1. **Exclude the record** from search results (Silent filtering).
2. **Raise an AccessDeniedError** for direct lookup.

---

## 4. The Unified Authentication API

Eden provides a single, unified entry point for authentication and session management.

```python
from eden.auth import authenticate, login

# 1. Authenticate credentials
user = await authenticate(request, email="...", password="...")

# 2. Start the session (automatically attaches to current tenant)
if user:
    await login(request, user)
```

### Key Security Features

- **Salted Hashing**: High-entropy Argon2id password hashing by default.
- **CSRF Protection**: Native middleware for all state-changing requests.
- **Brute-Force Protection**: Automatic login throttling and account lockout.
- **MFA (Opt-in)**: Built-in support for TOTP and WebAuthn.

---

**Next: [The Model-to-Form Bridge](../recipes/forms-and-validation.md) →**
