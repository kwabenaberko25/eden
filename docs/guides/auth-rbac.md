# Role-Based Access Control (RBAC) 👑

Eden provides a granular, tenant-aware permission system that allows you to secure your application at the role and permission levels — across both backend routes and frontend templates.

## Roles vs. Permissions

- **Roles**: Broad categories of users (e.g., `admin`, `manager`, `editor`).
- **Permissions**: Specific atomic actions a user can perform (e.g., `can_delete_post`, `can_publish`).

In Eden, roles typically act as containers for permissions.

---

## Defining a Role Hierarchy

You can define a hierarchy where higher roles automatically inherit permissions from lower roles.

```python
from eden.auth import RoleHierarchy

hierarchy = RoleHierarchy({
    "superadmin": ["admin", "manager", "user"],
    "admin": ["manager", "user"],
    "manager": ["user"],
    "user": []
})

# Attach to app state
app.state.role_hierarchy = hierarchy
```

---

## Securing Routes

### The `@roles_required` Decorator

Requires the user to have **all** of the specified roles.

```python
from eden.auth import roles_required

@app.get("/admin/settings")
@roles_required(["admin"])
async def admin_settings(request):
    return render_template("admin/settings.html")
```

### The `@permissions_required` Decorator

Requires the user to have **all** of the specified permissions.

```python
from eden.auth import permissions_required

@app.post("/posts/{id}/delete")
@permissions_required(["can_delete_posts"])
async def delete_post(request, id: int):
    post = await Post.get(id)
    await post.delete()
    return redirect("/posts")
```

### The `@require_any_role` Decorator

Grants access if the user has **at least one** of the listed roles.

```python
from eden.auth import require_any_role

@app.get("/reports")
@require_any_role(["admin", "analyst", "manager"])
async def view_reports(request):
    ...
```

### The `@require_any_permission` Decorator

Grants access if the user has **at least one** of the listed permissions.

```python
from eden.auth import require_any_permission

@app.post("/content")
@require_any_permission(["create_posts", "edit_posts"])
async def manage_content(request):
    ...
```

### Single Shorthand: `@require_role` and `@require_permission`

When you only need to check a single role or permission:

```python
from eden.auth import require_role, require_permission

@app.get("/admin")
@require_role("admin")
async def admin_only(request):
    ...

@app.delete("/users/{id}")
@require_permission("delete_users")
async def delete_user(request, id: int):
    ...
```

### Superuser Bypass

All role-based and permission-based decorators automatically grant access when `user.is_superuser` evaluates to `True`. This prevents accidental lockout and simplifies development.

### CBV Support via `@view_decorator`

Apply auth decorators to all methods of a Class-Based View:

```python
from eden.auth import login_required, roles_required, view_decorator
from eden.routing import View

@view_decorator(roles_required(["admin"]))
class AdminView(View):
    async def get(self, request):
        return {"panel": "admin"}

    async def post(self, request):
        # Also protected by roles_required
        ...
```

> [!IMPORTANT]
> All decorators use `_find_request()` internally to locate the Request object in both function-based views and CBVs. This means they work transparently regardless of view type.

---

## Tenant-Aware RBAC

In multi-tenant applications, a user may have different roles in different tenants. Eden's decorators automatically resolve tenant-scoped roles when the current tenant context is set.

### How It Works

1. The `TenantMiddleware` sets the current tenant on each request.
2. When a decorator checks roles, it calls `_get_tenant_roles(user)` which:
   - First checks for `user.get_roles_for_tenant(tenant_id)` method
   - Falls back to `user.tenant_roles` attribute
   - Falls back to `user.roles` (flat list)

### Implementation

```python
from eden.db import Model

class User(Model):
    async def get_roles_for_tenant(self, tenant_id: str) -> list[str]:
        """Return roles scoped to this specific tenant."""
        memberships = await TenantMembership.filter(
            user_id=self.id,
            tenant_id=tenant_id
        )
        return [m.role for m in memberships]

    async def get_permissions_for_tenant(self, tenant_id: str) -> list[str]:
        """Return permissions scoped to this specific tenant."""
        roles = await self.get_roles_for_tenant(tenant_id)
        perms = set()
        for role in roles:
            role_perms = await RolePermission.filter(role=role)
            perms.update(p.permission for p in role_perms)
        return list(perms)
```

---

## Dynamic Checks in Logic

Sometimes decorators aren't enough, and you need to check permissions inside your function body.

```python
async def update_profile(request):
    user = request.user

    # Superuser bypass
    if user.is_superuser:
        ...

    # Check if user can edit this specific profile
    if not user.has_permission("can_edit_others"):
        raise PermissionDenied("Access Denied")
```

---

## Usage in Templates

Eden's templating engine provides RBAC-aware directives for controlling UI elements:

### `@can` / `@cannot` Directives

```html
@can("delete_posts") {
    <button class="btn-danger">Delete Post</button>
}

@cannot("view_admin") {
    <div class="alert alert-warning">
        You do not have access to this feature.
    </div>
}
```

### Role-Based Rendering

```html
@auth("admin") {
    <a href="/admin" class="nav-link">Admin Panel</a>
}

@guest {
    <a href="/login" class="btn">Sign In</a>
}
```

> [!TIP]
> `@can` checks `request.user.has_permission()` while `@auth` checks `request.user.role`. Use `@can` for fine-grained permission checks and `@auth` for role-based UI sections.

---

## Row-Level Security (RLS)

A common pattern is restricting a query based on the user's role.

```python
async def list_documents(request):
    query = Document.query()

    # Non-admins only see their own documents
    if not request.user.has_role("admin"):
        query = query.filter(owner_id=request.user.id)

    documents = await query.all()
    return render_template("docs.html", documents=documents)
```

---

## Complete Decorator Reference

| Decorator | Behavior | CBV Support |
| :--- | :--- | :--- |
| `@login_required` | Requires authenticated user | ✅ |
| `@roles_required(["..."])` | Requires **all** listed roles | ✅ |
| `@permissions_required(["..."])` | Requires **all** listed permissions | ✅ |
| `@require_role("...")` | Requires a single role | ✅ |
| `@require_permission("...")` | Requires a single permission | ✅ |
| `@require_any_role(["..."])` | Requires **any one** of the listed roles | ✅ |
| `@require_any_permission(["..."])` | Requires **any one** of the listed permissions | ✅ |
| `@view_decorator(dec)` | Applies any decorator to all CBV methods | ✅ |
| `@bind_user_principal` | Attaches user to request from auth backend | ✅ |

All decorators support:

- **Superuser bypass** (`user.is_superuser`)
- **Tenant-aware resolution** (via `_get_tenant_roles` / `_get_tenant_permissions`)
- **CBV via `_find_request`** (automatically finds Request in args/kwargs)

---

**Next Steps**: [Social Login (OAuth)](auth-oauth.md)
