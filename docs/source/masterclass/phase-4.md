# Phase 4: The Branches (Security, RBAC & Isolation) 🛡️

Once your data is modeled and your UI is interactive, the single most critical task is securing it. Modern SaaS applications require complex security constraints: Who is this user? What roles do they have? Are they accessing data for the correct Organization/Tenant?

Eden fundamentally simplifies this incredibly complex domain through built-in Authentication, Role-Based Access Control (RBAC), and native Multi-Tenancy.

---

## 🔐 1. Authentication & Social Logins

Eden provides a highly extensible `BaseUser` mixin. Instead of reinventing passwords and session management, you inherit security best practices immediately.

### Defining Your User

```python
from eden.db import Model, f
from eden.auth.models import BaseUser

# BaseUser automatically adds email, password_hash, is_active, is_staff, is_superuser, roles, and permissions!
class User(Model, BaseUser):
    __tablename__ = "users"
    
    # Custom fields for your app
    department: str | None = f(nullable=True)
    bio: str | None = f(max_length=500, nullable=True)
```

---

### 🌐 Social Logins (OAuth) Masterclass

Eden's `OAuthManager` handles the heavy lifting of state validation, token exchange, and user profile mapping. Here is how you set up GitHub login in your `nexus.py` (or `app/__init__.py`):

```python
from eden.auth.oauth import OAuthManager

oauth = OAuthManager()

# 1. Register the provider
oauth.register_github(
    client_id="YOUR_GITHUB_CLIENT_ID",
    client_secret="YOUR_GITHUB_CLIENT_SECRET",
    # Optional: custom handler after successful login
    # on_login=my_custom_handler 
)

# 2. Mount the routes
# This creates /auth/oauth/github/login and /auth/oauth/github/callback
oauth.mount(app)
```

4. **Auto-Link**: If the email matches an existing user, Eden links the social account. If not, it creates a new `User` record automatically.

---

---

## 🛡️ 2. Role-Based Access Control (RBAC)

Checking `if user.is_superuser:` is fine for basic apps, but enterprise apps need granular permissions. Eden includes a hierarchical RBAC engine: `EdenRBAC`.

### Technical Deep Dive: Defining Hierarchies

You define your roles exactly once, typically in your app startup configuration. Notice how permissions flow **upwards** through the parent/child relationships.

```python
from eden.auth.rbac import default_rbac

# 1. Define base permissions
default_rbac.add_role("viewer")
default_rbac.add_permission("viewer", "read:posts")

# 2. Define an editor that inherits from viewer
default_rbac.add_role("editor", parents=["viewer"])
default_rbac.add_permission("editor", "write:posts")
default_rbac.add_permission("editor", "edit:posts")

# 3. Define a manager that inherits from editor
# Manager now has: delete:posts + edit:posts + write:posts + read:posts!
default_rbac.add_role("manager", parents=["editor"])
default_rbac.add_permission("manager", "delete:posts")
```

### ⚡ Enforcing Permissions with Decorators

While you can check permissions manually, the **Eden-way** is to use declarative decorators on your views. This keeps your business logic clean and your security audits easy.

```python
from eden import login_required, roles_required, require_permission

# 1. Broadest: User must be logged in
@app.get("/dashboard")
@login_required
async def dashboard(request):
    return {"user": request.user.email}

# 2. Middle: User must have one of these specific roles
@app.get("/admin/settings")
@roles_required(["admin", "manager"])
async def admin_settings(request):
    return {"status": "authorized"}

# 3. Deepest: User must have a specific permission (inherited or direct)
@app.post("/posts/delete/{id}")
@require_permission("delete:posts")
async def delete_post(request, id: int):
    # This view is ONLY reachable by "manager" or "superuser"
    await Post.delete(id)
    return {"message": "Post nuked! 🚀"}
```

---

## 🏢 3. Advanced Multi-Tenancy & Isolation

Multi-tenancy is where multiple organizations share the same app instance but their data remains entirely isolated. 

### Multi-Schema Isolation (Postgres)

For ultra-secure enterprise apps, Eden supports **Postgres Schema Isolation**. This is the "Gold Standard" of data isolation.

**How it works:**
1.  **Resolution**: The `TenantMiddleware` extracts the tenant slug (e.g., `acme`) from the subdomain.
2.  **Activation**: Before your view code runs, Eden executes `SET search_path TO acme, public;` on the database connection.
3.  **Encapsulation**: Your SQL queries (e.g., `SELECT * FROM tasks`) automatically point to the `acme.tasks` table. Users in `globex.myapp.com` literally cannot see the tables of `acme.myapp.com`.

```python
# app/settings.py
TENANT_STRATEGY = "subdomain" 
TENANT_ISOLATION = "schema" # Switches schemas automatically!
```

### Manual Row-Level Security (RLS)

If you prefer a shared database table, you simply filter by the `tenant_id` which is injected into the context automatically.

```python
from eden import get_current_tenant

@app.get("/projects")
async def list_projects(request):
    tenant = get_current_tenant()
    
    # RLS Enforcement: We ONLY ever query projects belonging to this tenant context
    projects = await Project.filter(tenant_id=tenant.id)
    
    return request.app.render("projects/list.html", {"projects": projects})
```

---

---

### 🎉 Phase 4 Complete

You have successfully secured the application. You can authenticate users via OAuth, enforce granular hierarchical permissions via decorators, and isolate data using Postgres Schemas!

**Up Next: [Phase 5: The Leaves (Advanced Capabilities & Integrations)](./phase-5.md)**
