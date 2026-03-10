# Task 7: Secure Application with Middleware & RBAC

**Goal**: Transform your application into a production-hardened platform using global security layers and Role-Based Access Control (RBAC).

---

## 🛡️ Step 7.1: Global Security Middleware

Eden includes enterprise-grade middleware that can be activated with a single line of code.

**File**: `app/__init__.py`

```python
def create_app() -> Eden:
    app = Eden(...)
    
    # ── Security Suite ───────────────────────────────────────────────────
    
    # 1. Security Headers: CSP, HSTS, XSS Protection
    app.add_middleware("security")  
    
    # 2. CSRF Defense: Cross-Site Request Forgery protection
    app.add_middleware("csrf")      
    
    # 3. Rate Limiting: Prevent brute force and DDoS
    app.add_middleware("ratelimit", max_requests=60, window_seconds=60)
    
    # 4. CORS: Control cross-origin resource sharing
    app.add_middleware("cors", allow_origins=["*"])
    
    # 5. Session: Secure encrypted cookies for authentication
    app.add_middleware("session", secret_key=SECRET_KEY)
    
    return app
```

### Why use Global Middleware?

- **Unified Defense**: Every single request is automatically screened for common vulnerabilities before reaching your routes.
- **Zero Config**: Eden provides sensible defaults for each layer, but they are fully customizable via `kwargs`.

---

## 🚦 Step 7.2: Granular Access Control (RBAC)

Use Eden's high-fidelity decorators to restrict access to specific views based on authentication status or roles.

**File**: `app/routes/admin.py`

```python
from eden.auth import roles_required, login_required

@admin_router.get("/metrics")
@roles_required(["admin", "superadmin"])
async def dashboard_metrics():
    """Only admins can see system analytics."""
    return {"active_users": 450, "revenue": 12000}

@admin_router.get("/profile")
@login_required()
async def user_profile(request):
    """Any authenticated user can see their profile."""
    return {"user": request.user.name}
```

---

## 🔑 Step 7.3: Programmatic Security Gates

Sometimes you need to check permissions inside your function logic rather than with a decorator.

```python
from eden.exceptions import Forbidden

@user_router.delete("/{user_id}")
async def remove_user(request, user_id: int):
    # Check if the current user owns the resource or is an admin
    if not request.user.is_admin and request.user.id != user_id:
        raise Forbidden("You do not have permission to delete this user.")
        
    user = await User.get(id=user_id)
    await user.delete()
    return {"status": "removed"}
```

> [!CAUTION]
> Always use `Forbidden` or `Unauthorized` exceptions from `eden.exceptions` to ensure the framework renders the correct "Premium Error Page" to the user.

---

### **Next Task**: [Integrating SaaS Features](./task8_saas.md)
