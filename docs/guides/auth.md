# Authentication & Security 🛡️

Eden provides a modular, industrial-grade security suite designed to handle everything from simple blogs to complex multi-tenant SaaS platforms.

## Core Philosophy

Security in Eden is built on three pillars:

- **Async-First**: All authentication flows are non-blocking.
- **Convention over Configuration**: Batteries-included defaults that are safe out of the box.
- **Multi-Layered**: Authentication, Authorization, and Audit work together seamlessly.

---

## The `User` Model

All authentication revolves around the `User` model. Eden provides a `BaseUser` that includes standard security fields, which you can extend.

```python
from eden.auth import User

# Check status easily
if request.user.is_authenticated:
    print(f"Hello, {request.user.name}")
```

---

## Authorization Decorators

Eden offers a comprehensive set of decorators for protecting routes. All decorators work with both **function-based views** and **Class-Based Views (CBVs)**.

### `@login_required`

The simplest guard — requires an authenticated user.

```python
from eden.auth import login_required

@app.get("/dashboard")
@login_required
async def dashboard(request):
    return request.render("dashboard.html")
```

### `@roles_required`

Restrict access to users with specific roles. All listed roles must be present.

```python
from eden.auth import roles_required

@app.get("/admin")
@roles_required(["admin"])
async def admin_panel(request):
    return {"panel": "admin"}
```

### `@permissions_required`

Restrict access to users with specific permissions. All listed permissions must be present.

```python
from eden.auth import permissions_required

@app.delete("/posts/{id}")
@permissions_required(["delete_posts"])
async def delete_post(request, id: int):
    ...
```

### `@require_any_role` / `@require_any_permission`

Match if the user has **at least one** of the specified roles or permissions.

```python
from eden.auth import require_any_role, require_any_permission

@app.get("/reports")
@require_any_role(["admin", "analyst"])
async def view_reports(request):
    ...

@app.post("/content")
@require_any_permission(["create_posts", "edit_posts"])
async def manage_content(request):
    ...
```

### `@require_permission` / `@require_role`

Single-permission or single-role shorthand decorators.

```python
from eden.auth import require_permission, require_role

@app.get("/admin")
@require_role("admin")
async def admin_only(request):
    ...

@app.delete("/users/{id}")
@require_permission("delete_users")
async def delete_user(request, id: int):
    ...
```

### `@view_decorator` — Applying Decorators to CBVs

For Class-Based Views, use `view_decorator` to apply auth decorators to all HTTP methods on the view.

```python
from eden.auth import login_required, view_decorator
from eden.routing import View

@view_decorator(login_required)
class ProfileView(View):
    async def get(self, request):
        return {"user": request.user.name}

    async def post(self, request):
        # Also protected by login_required
        data = await request.form()
        ...
```

### Superuser Bypass

All role and permission decorators automatically grant access to users where `user.is_superuser` is `True`. This prevents lockout of admin accounts and simplifies development.

### Tenant-Aware RBAC

When working in a multi-tenant application, role and permission checks automatically consider the **current tenant context**. If your `User` model provides a `get_roles_for_tenant()` or `get_permissions_for_tenant()` method, Eden will use those to resolve tenant-scoped access.

```python
class CustomUser(User):
    async def get_roles_for_tenant(self, tenant_id):
        """Return roles specific to this tenant."""
        return await TenantRole.filter(user_id=self.id, tenant_id=tenant_id)
```

---

## Security Middleware Suite 🧱

Eden protects your app automatically when you enable the security suite.

```python
app.add_middleware("security")  # CSP, HSTS, X-Frame-Options
app.add_middleware("csrf")      # Cross-Site Request Forgery
app.add_middleware("ratelimit") # Bruteforce protection
```

---

## Template Authorization Directives

Eden integrates RBAC directly into your templates via the `@can` / `@cannot` directives:

```html
@can("delete_users") {
    <button class="btn-danger">Delete User</button>
}

@cannot("view_admin") {
    <p>You do not have access to the admin panel.</p>
}
```

These check `request.user.has_permission()` under the hood — the same permission system used by backend decorators.

---

## Technical Guides

Explore specialized guides for each part of the security system:

### 1. [Session Management](sessions.md)

Learn about secure cookies, session lifecycles, and how Eden remembers users.

### 2. [Role-Based Access (RBAC)](auth-rbac.md)

Define roles like `admin` and `editor` and protect routes using decorators like `@roles_required`.

### 3. [Social Login (OAuth)](auth-oauth.md)

Integrate Google, GitHub, and other providers with zero-friction onboarding.

### 4. [Multi-Tenancy Patterns](tenancy.md)

Learn how `TenantMixin` ensures data isolation in shared database environments.

---

## Security Checklist

Before going to production, ensure:

- [ ] `DEBUG` is set to `False`.
- [ ] `SECRET_KEY` is a long, random string (minimum 32 characters for JWT).
- [ ] All forms use the `@csrf` directive.
- [ ] `SESSION_COOKIE_SECURE` is `True` (requires HTTPS).
- [ ] Rate limits are applied to sensitive routes (Login, Signup).
- [ ] Role and permission decorators protect all admin and destructive endpoints.
- [ ] Tenant isolation is verified if running a multi-tenant deployment.

---

---

## Administrative Access 👑

Eden includes built-in support for administrative users who bypass standard permission checks (`is_superuser`).

### Creating an Admin Account

Once you have initialized and migrated your database, use the CLI to create your first administrative user:

```bash
eden auth createsuperuser
```

The command will interactively prompt you for:
- **Email**: Used as the primary login identifier.
- **Full Name**: The display name for the user.
- **Password**: Securely hashed using Eden's performance-optimized hashers.

> [!NOTE]
> Superusers automatically pass all `@roles_required` and `@permissions_required` guards, making them ideal for initial setup and system maintenance.

---

**Next Steps**: [Templating System](templating.md)
