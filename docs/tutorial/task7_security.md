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
from eden.auth import login_required, can_read, can_write

@admin_router.get("/metrics")
@can_read("system_stats")  # Checks if user has 'read' permission for resource
async def dashboard_metrics():
    """Only admins with specific permissions can see system analytics."""
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
from eden.auth import check_permission

@user_router.delete("/{user_id}")
async def remove_user(request, user_id: int):
    # Programmatic check using the auth engine
    if not await check_permission(request.user, "delete", "user", resource_id=user_id):
        raise Forbidden("You do not have permission to delete this user.")
        
    user = await User.get(id=user_id)
    await user.delete()
    return {"status": "removed"}
```

> [!CAUTION]
> Always use `Forbidden` or `Unauthorized` exceptions from `eden.exceptions` to ensure the framework renders the correct "Premium Error Page" to the user.

---

## 🔏 Step 7.4: Advanced Permission Checking

Use custom permission classes for granular row-level control:

```python
from eden.auth import has_permission

class PostPermission:
    """Custom permission check for blog posts."""
    
    @staticmethod
    async def can_edit(user, post_id: int):
        """Only let users edit their own posts."""
        post = await Post.get(id=post_id)
        return post.user_id == user.id or user.is_admin

# In your route:
@post_router.put("/{post_id}")
async def edit_post(request, post_id: int):
    """Edit a post (permission-checked)."""
    if not await PostPermission.can_edit(request.user, post_id):
        raise Forbidden("You can only edit your own posts")
    
    data = await request.json()
    post = await Post.get(id=post_id)
    await post.update(**data)
    return {"message": "Post updated"}
```

---

## 🛡️ Step 7.5: Session Security Best Practices

Configure your session middleware properly:

```python
# app/__init__.py
def create_app():
    app = Eden(...)
    
    # Secure session configuration
    app.add_middleware(
        "session",
        secret_key=SECRET_KEY,
        session_cookie={
            "key": "session",
            "httponly": True,      # Prevent JS from reading cookies
            "secure": not DEBUG,   # HTTPS only in production
            "samesite": "strict",  # CSRF protection
            "max_age": 3600        # 1 hour timeout
        }
    )
    
    return app
```

Then validate sessions in your middleware:

```python
# Custom middleware to check session validity
@app.middleware("http")
async def validate_session(request, call_next):
    """Validate user session on every request."""
    if request.user and not request.user.is_active:
        # Log the user out
        del request.session['user_id']
        return redirect("/login")
    
    response = await call_next(request)
    return response
```

---

## 🔐 Step 7.6: Password Hashing & Authentication

Never store plain text passwords. Eden handles this automatically:

```python
from eden.auth import hash_password, verify_password

class AuthSchema(Schema):
    email: EmailStr
    password: str = field(min_length=8, widget="password")

@auth_router.post("/register")
async def register(request, credentials: AuthSchema):
    """Register a new user with secure password hashing."""
    # Check if email already exists
    existing = await User.filter(email=credentials.email).exists()
    if existing:
        raise ValueError("Email already registered")
    
    # Password is automatically hashed by Eden
    user = await User.create(
        email=credentials.email,
        password=credentials.password  # Eden hashes this
    )
    
    return {"message": "User registered successfully"}

@auth_router.post("/login")
async def login(request, credentials: AuthSchema):
    """Authenticate user and create session."""
    user = await User.filter(email=credentials.email).first()
    
    if not user or not verify_password(credentials.password, user.password):
        raise Unauthorized("Invalid email or password")
    
    # Set session (Eden handles cookie creation)
    request.session['user_id'] = str(user.id)
    request.session['user_email'] = user.email
    
    return {"message": "Logged in successfully", "user": user.to_dict()}
```

---

## 🚫 Step 7.7: CSRF Token Protection in Forms

Always protect form submissions:

```html
@extends("layouts/base")

@section("content") {
    <form method="POST" action="/settings/change-password" class="form">
        <!-- CSRF token is automatically injected -->
        @csrf
        
        <div class="form-group">
            <label>Current Password</label>
            <input type="password" name="current_password" required>
        </div>
        
        <div class="form-group">
            <label>New Password</label>
            <input type="password" name="new_password" required>
        </div>
        
        <button type="submit" class="btn btn-primary">Change Password</button>
    </form>
}
```

The `@csrf` directive automatically:
1. Generates a unique token
2. Stores it in the session
3. Injects it as a hidden field
4. Eden validates it on POST automatically

---

## 📊 Step 7.8: Audit Logging & Compliance

Log security-relevant events for compliance:

```python
from datetime import datetime

class AuditLog(Model):
    """Track all user actions for compliance."""
    user_id: Mapped[int] = f(foreign_key="user.id")
    action: Mapped[str] = f(max_length=50)  # e.g., "login", "file_download"
    resource: Mapped[str | None] = f(max_length=255)  # e.g., "document_123"
    ip_address: Mapped[str] = f(max_length=45)
    user_agent: Mapped[str] = f()
    created_at: Mapped[datetime] = f(default=datetime.utcnow)

# Audit middleware
@app.middleware("http")
async def audit_log_middleware(request, call_next):
    """Log sensitive actions."""
    response = await call_next(request)
    
    # Log if user is authenticated and action is sensitive
    if request.user and request.method in ["POST", "DELETE", "PUT"]:
        await AuditLog.create(
            user_id=request.user.id,
            action=request.method,
            resource=request.url.path,
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent", "")
        )
    
    return response
```

---

### **Next Task**: [Integrating SaaS Features](./task8_saas.md)
