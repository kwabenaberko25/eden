# 👑 Role-Based Access Control (RBAC)

**Granular, tenant-aware identity management. Eden provides a high-security access control system that allows you to secure your SaaS architecture at the role and permission levels—across both backend routes and frontend templates.**

---

## 🧠 Conceptual Overview

Eden’s RBAC system is built for Enterprise SaaS. It supports hierarchical roles (where an "Admin" automatically inherits "User" permissions) and understands that in a multi-tenant world, a user’s role changes depending on which Organization they are currently viewing.

### The Security Handshake

```mermaid
graph TD
    A["Request to /admin/settings"] --> B["Eden: Auth Middleware"]
    B --> C{"Authenticated?"}
    C -- "Yes" --> D["Eden: RBAC Decorator"]
    D --> E{"User is Superuser?"}
    E -- "Yes" --> F["Access Granted: God Mode"]
    E -- "No" --> G["Fetch Tenant-Scoped Roles"]
    G --> H["Resolve Role Hierarchy"]
    H --> I{"Permission Found?"}
    I -- "Yes" --> J["Access Granted"]
    I -- "No" --> K["Reject: 403 Forbidden"]
```

---

## 🏗️ Relational RBAC (SQL-Backed)

For production applications, Eden recommends using the **Relational RBAC** system. This stores roles and permissions in your database, allowing you to manage them via the **Admin Panel** without code changes.

### 1. The Relational Models

Eden provides built-in models for Roles and Permissions that support deep hierarchy.

```python
from eden.auth.models import Role, Permission

# Roles inherit permissions from their parents
role_user = Role(name="user")
role_editor = Role(name="editor", parents=[role_user])
role_admin = Role(name="admin", parents=[role_editor])

# Assign permissions
perm_view = Permission(name="post:view")
perm_edit = Permission(name="post:edit")

role_user.permissions = [perm_view]
role_editor.permissions = [perm_edit]
```

### 2. Recursive Resolution

When you check `user.has_permission("post:view")`, Eden recursively traverses the role tree:

1. It checks the user's direct roles.
2. It follows parent relationships (e.g., Admin -> Editor -> User).
3. It collects all permissions from the entire lineage.
4. It merges them with any legacy JSON overrides (backward compatibility).

### 3. Admin Panel Management

Once enabled, these models appear automatically in the **Eden Admin Panel**, allowing you to:

- Create new functional permissions.
- Build complex role hierarchies visually.
- Assign roles to users via a premium multi-select interface.

---

## 🏗️ In-Memory Hierarchy (Lightweight)

For simple applications or testing, you can use the lightweight `RoleHierarchy` handler.

```python
from eden.auth.access import RoleHierarchy

# 1. Initialize the Hierarchy Handler
rbac = RoleHierarchy()

# 2. Define Hierarchy (Role, Parents - roles it inherits FROM)
rbac.add_role("user")
rbac.add_role("editor", parents=["user"])
rbac.add_role("admin", parents=["editor"])

# 3. Assign Atomic Permissions to Roles
rbac.add_permission("user", "view_posts")
rbac.add_permission("editor", "edit_posts")
```

---

## 🚀 Securing Backend Routes

Eden provides a suite of decorators designed for readability and reliability. They automatically handle the current request context and support both function-based views and class-based views.

### 1. Simple Role Guards

```python
from eden import Eden
from eden.auth import require_role, roles_required

app = Eden()

@app.get("/admin/logs")
@require_role("admin")
async def view_logs(request):
    return {"logs": "..."}

# Requires multiple roles
@app.get("/billing")
@roles_required(["admin", "billing_manager"])
async def billing_view(request):
    return {"billing": "..."}
```

### 2. Fine-Grained Permission Guards

Avoid hardcoding roles in your logic. Instead, check for specific *permissions*. This makes your code more resilient to role structure changes.

```python
from eden import Eden
from eden.auth import require_permission

app = Eden()

@app.post("/posts/delete/{id}")
@require_permission("delete_posts")
async def delete_post(request, id: int):
    return {"status": "deleted"}
```

### 3. Class-Based View (CBV) Protection

Secure an entire resource by applying decorators to the class.

```python
from eden.auth import view_decorator, roles_required
from eden.routing import View

@view_decorator(roles_required(["admin"]))
class AdminPanel(View):
    async def get(self, request):
        return {"admin": "panel"}
        
    async def post(self, request):
        # Also protected automatically
        return {"saved": True}
```

---

## ⚡ Tenant-Aware RBAC

In SaaS, a user is rarely "just an Admin." They are an "Admin of Organization A" but perhaps only a "Member of Organization B." Eden's guards automatically call `request.user.get_roles_for_tenant(tenant_id)` to resolve roles in context.

```python
from eden.db import Model, f, Mapped

class Membership:
    @classmethod
    async def get_by(cls, **kwargs):
        # Mocking membership retrieval
        return type("Membership", (), {"role": "admin"})

# In your User model
class User(Model):
    __tablename__ = "users_custom"
    async def get_roles_for_tenant(self, tenant_id: str) -> list[str]:
        # Fetch role from memberships table
        membership = await Membership.get_by(user_id=self.id, tenant_id=tenant_id)
        return [membership.role] if membership else []
```

---

## 🎨 RBAC in Templates

Eden’s templating engine provides semantic directives for controlling your UI based on identity.

### `@can` / `@cannot` (Permissions)

```html
@can("delete_posts") {
    <button class="btn btn-danger" hx-delete="/posts/{{ post.id }}">
        Delete Post
    </button>
}
```

### `@auth` / `@guest` (Status & Role)

```html
@auth("admin") {
    <a href="/admin">Admin Dashboard</a>
}

@guest {
    <a href="/login" class="btn">Sign In</a>
}
```

---

## 📄 API Reference

### RBAC Decorators

| Decorator | Description |
| :--- | :--- |
| `@require_role` | User must have a specific role (supports hierarchical parents). |
| `@require_permission` | User must have a specific functional permission. |
| `@roles_required` | User must possess **ALL** of the listed roles. |
| `@permissions_required` | User must possess **ALL** listed permissions. |
| `@require_any_role` | Access granted if user has **AT LEAST ONE** listed role. |
| `@require_any_permission` | Access granted if user has **AT LEAST ONE** listed permission. |

### Superuser Bypass

All checks include a "God Mode" bypass. If `request.user.is_superuser` is `True`, all decorators automatically grant access. This is essential for administrative troubleshooting.

---

## 🔐 Interaction with Multi-Tenancy (RLS)

Eden's RBAC system works in tandem with the **Row-Level Security (RLS)** layer. When a user is authenticated and a tenant context is established, the following handshake occurs:

1. **Identity Resolution**: The RBAC layer verifies the user has the correct `role` or `permission` for the current tenant.
2. **Automatic Filtering**: Even if a user has "Admin" permissions, the database layer automatically injects a `tenant_id` filter into every query if the model is marked as tenant-isolated.
3. **Cross-Tenant Prevention**: This ensures that even a malicious request or a bug in a custom query cannot accidentally leak data from Tenant A to an Admin of Tenant B.

### Hybrid Tenancy (Opt-Out)

For models that should be globally accessible (e.g., shared `ProductCatalog` or `GlobalSettings`), you can explicitly opt-out of isolation to prevent the automatic `tenant_id` filter from being applied.

```python
from eden.db import Model
from eden.tenancy import tenant_isolated

@tenant_isolated(enabled=False)
class GlobalProduct(Model):
    # This model will NOT be filtered by the current tenant context
    name: str = StringField(max_length=255)
```

For more details on data isolation, see the [Multi-Tenancy Guide](./tenancy.md).

---

## 💡 Best Practices

1. **Prefer Permissions over Roles**: Check for `@can("edit_settings")` rather than `@auth("admin")`. This allows you to create custom roles later without changing your code.
2. **Audit Logs**: Use Eden’s `telemetry` features to log whenever a permission check fails—this is an early warning sign for potential security probes.
3. **Fail-Secure**: Eden’s decorators return a `403 Forbidden` response by default if any check fails, ensuring your application remains "Secure by Default."

---

**Next Steps**: [Social Login (OAuth)](auth-oauth.md)
