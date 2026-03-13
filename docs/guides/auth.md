# Authentication & Security 🛡️

Eden provides a comprehensive, session-based and token-based authentication system designed for both traditional web apps and modern APIs.

> **Advanced Auth Patterns?** See [Multi-Backend Authentication](multi-backend-auth.md) for chaining multiple backends, custom implementations, and caching strategies.

## Core Models

### `User` & `BaseUser`

The foundation of identity in Eden. `BaseUser` provides the fields and methods for authentication, while `User` is the default implementation.

```python
from eden.auth import User

# Properties
user.is_authenticated  # True/False
user.email
user.roles             # ['admin', 'user']
user.permissions       # ['can_edit', 'can_delete']
user.is_superuser      # True if superuser

```

### Social Accounts
Eden supports linking multiple social providers to a single user account.

---

## Role-Based Access Control (RBAC) 👑

Eden uses a simple yet powerful role-based system. Roles are strings, and you can restrict access to routes using decorators.

### Role Hierarchy

Eden supports role hierarchy for complex permission models:

```python
from eden import Eden
from eden.auth import Role, RoleHierarchy

app = Eden(__name__)

# Define a hierarchy: 'superadmin' > 'admin' > 'manager' > 'user'
hierarchy = RoleHierarchy({
    'superadmin': ['admin', 'manager', 'user'],
    'admin': ['manager', 'user'],
    'manager': ['user'],
    'user': []
})

# Now any permission check for 'admin' also grants 'manager' and 'user' access
```

### Restricting Access

| Decorator | Argument | Description |
| :--- | :--- | :--- |
| `@login_required` | None | Requires any authenticated user. |
| `@roles_required` | `list[str]` | Requires at least one of these roles. |
| `@permissions_required` | `list[str]` | Requires ALL of these permissions. |
| `@require_permission` | `str` | Checks hierarchy (admin > manager). |

### Roles & Permissions

You can secure endpoints using roles and permissions.

```python
from eden.auth import roles_required, require_permission

@app.get("/admin")
@roles_required(["admin"])
async def admin_dashboard(request):
    return render_template("admin.html")

@app.post("/posts/{id}")
@require_permission("can_edit_posts")
async def edit_post(request, id: str):
    # Only users with 'can_edit_posts' permission, or admin+ role
    post = await Post.get(id=id)
    return json({"updated": True})
```

### Dynamic Permissions

Assign permissions to roles or individual users:

```python
# Assign to role
user.add_role("editor")
user.grant_permission("can_publish")

# Check at runtime
if user.has_permission("can_delete"):
    await post.delete()
```


---

## Social Login (OAuth 2.0)

Eden supports Google and GitHub OAuth out of the box. Perfect for modern applications that want to reduce account friction.

### Setup Steps

#### 1. Create OAuth Applications

**Google:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new OAuth 2.0 credentials (Web Application)
3. Set Authorized Redirect URI: `https://yourdomain.com/auth/oauth/google/callback`

**GitHub:**
1. Go to Settings → Developer Settings → OAuth Apps
2. Create new OAuth App
3. Set Authorization callback URL: `https://yourdomain.com/auth/oauth/github/callback`

#### 2. Configure Environment

Add your credentials to `.env`:

```bash
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
```

#### 3. Mount OAuth Routes

```python
import os
from eden import Eden
from eden.auth.oauth import OAuthManager

app = Eden(__name__)

oauth = OAuthManager()

# Register providers
oauth.register_google(
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET")
)

oauth.register_github(
    client_id=os.getenv("GITHUB_CLIENT_ID"),
    client_secret=os.getenv("GITHUB_CLIENT_SECRET")
)

# Mount OAuth routes at /auth/oauth/{provider}/login
oauth.mount(app)
```

### OAuth Routes

Once mounted, the following routes are automatically available:

| Route | Purpose |
|-------|---------|
| `GET /auth/oauth/google/login` | Redirect user to Google login |
| `GET /auth/oauth/github/login` | Redirect user to GitHub login |
| `GET /auth/oauth/{provider}/callback` | OAuth callback (handled automatically) |
| `GET /auth/profile` | User profile & linked accounts |
| `POST /auth/oauth/{provider}/unlink` | Unlink social account |

### Handling OAuth Responses

After OAuth success, users are redirected to `next` parameter or home page:

```python
# In your template
<a href="/auth/oauth/google/login?next=/dashboard">Sign in with Google</a>
```

The OAuth flow automatically:
- Creates user account if new
- Links social account to existing user (if email matches)
- Sets appropriate user roles/permissions
- Creates session cookie

### OAuth Error Handling

Handle common OAuth failures:

```python
@app.get("/auth/oauth/{provider}/callback")
async def oauth_callback(request, provider: str):
    try:
        # OAuth manager handles callback automatically
        user = await oauth.handle_callback(request, provider)
        
        # Redirect to next page
        next_url = request.query_params.get("next", "/")
        return RedirectResponse(url=next_url)
        
    except oauth.InvalidStateError:
        # State token mismatch (CSRF attempt)
        return json({"error": "Invalid state parameter"}, status=400)
        
    except oauth.ProviderError as e:
        # Provider returned an error (e.g., user denied access)
        return json(
            {"error": f"{provider} error: {e.message}"},
            status=401
        )
        
    except oauth.TokenExpiredError:
        # OAuth token expired (rare)
        return json({"error": "Session expired"}, status=401)
        
    except Exception as e:
        # Unexpected error
        logger.error(f"OAuth error: {e}")
        return json({"error": "Authentication failed"}, status=500)
```

### Custom OAuth Callbacks

Customize user creation or linking:

```python
# Before mounting OAuth
@oauth.on_user_created()
async def setup_new_user(user, provider: str):
    # Give new OAuth users 'user' role
    await user.add_role("user")
    
    # Send welcome email
    await send_email(
        to=user.email,
        subject="Welcome!",
        template="welcome",
        context={"name": user.first_name or "Friend"}
    )

@oauth.on_account_linked()
async def on_link(user, provider: str, account: dict):
    # Log when users link social accounts
    await AuditLog.create(
        user=user,
        action=f"linked_{provider}",
        details={"account": account.get("email")}
    )
```

### Security Notes

- ✅ CSRF tokens validated automatically
- ✅ State parameter prevents attacks
- ✅ Secure session cookies (HttpOnly, SameSite=Lax)
- ✅ Email verification can be enforced
- ✅ Use HTTPS in production (redirects to http fail)

### Profile & Unlinking

Once mounted, Eden provides a `/profile` view where users can see linked accounts and unlink them. Note that unlinking the last remaining login method (if no password is set) is prevented for security.


---

## API Token Authentication 🔑

For stateless API access, Eden provides a secure, hashed API Key system.

### Generating a Key

```python
from eden import APIKey

# Generates a key object and the raw string (show this only once!)
api_key, raw_key = await APIKey.generate(
    session,
    user=request.user, 
    name="Mobile App Token"
)
```


### Using the Key
Clients should send the key in the `Authorization` header:
`Authorization: Bearer ed_...`

---

## Security Middleware Suite 🧱

Eden protects your app automatically when you enable the security middleware.

```python
app.add_middleware("security")  # CSP, HSTS, X-Frame-Options
app.add_middleware("csrf")      # CSRF Protection
app.add_middleware("ratelimit") # Rate Limiting
```

### CSRF in Templates

Always include the `@csrf` directive in your forms:

```html
<form method="POST">
    @csrf
    <input type="text" name="data">
    <button type="submit">Send</button>
</form>
```

---

## Security & Data Validation Reference 🛠️

Eden provides a comprehensive suite of validators in `eden.validators`. These can be used standalone or as Pydantic types.

| Validator | Type Hint | Description |
| :--- | :--- | :--- |
| `validate_email` | `EdenEmail` | RFC 5322 structural check. |
| `validate_phone` | `EdenPhone` | E.164 and local format validation. |
| `validate_password` | `str` | Checks length, case, digits, and special chars. |
| `validate_slug` | `EdenSlug` | Lowercase alphanumeric with hyphens. |
| `validate_url` | `EdenURL` | Full URL structure and scheme check. |
| `validate_ip` | `str` | IPv4/IPv6 validation. |
| `validate_credit_card` | `str` | Luhn algorithm + brand detection. |
| `validate_gps` | `Coordinate` | Latitude/Longitude range checks. |
| `validate_file_type` | `dict` | MIME type and file size (MB) validation. |
| `validate_iban` | `str` | International Bank Account Number. |
| `validate_national_id` | `str` | GH (NIA), US (SSN), GB (NI) support. |

### Usage Example
```python
from eden.validators import validate_email, validate_password

def register_view(request):
    email_res = validate_email(request.form.get("email"))
    pass_res = validate_password(request.form.get("password"))

    if not email_res.ok:
        return {"error": email_res.error}
```

---

## Password Security & Hashing 🔒

Eden uses **Argon2** (via `argon2-cffi`) by default for industry-leading password security. All User models inherit `set_password` and `check_password` methods that handle salting and hashing automatically.

---

## JWT Provider

For stateless API authentication, Eden ships with a `JWTProvider` (aliased from `JWTBackend`).

```python
from eden.auth.providers import JWTProvider

provider = JWTProvider(secret="top-secret", algorithm="HS256")

# Creating a token
token = provider.encode({"sub": user.id, "scope": "admin"}, expires_in=3600)

# Verifying a token
payload = provider.decode(token)
```

> **Note**: `encode()` accepts an optional `expires_in` parameter (in seconds).
> You can also use `create_access_token()` and `create_refresh_token()` for
> fine-grained control over token types.

---

## 🔐 Session Management & Lifecycle

Sessions are essential for tracking user state. Eden makes session management simple, secure, and performant.

### Session Lifecycle: Creating & Validating

**Scenario**: User logs in → create session → validate on each request → clean up on logout.

```python
from eden import Eden
from eden.auth import Session
from datetime import timedelta, datetime

app = Eden(__name__)

# Configure session settings
app.config.SESSION_COOKIE_NAME = "eden_session"
app.config.SESSION_COOKIE_SECURE = True  # HTTPS only
app.config.SESSION_COOKIE_HTTPONLY = True  # No JavaScript access
app.config.SESSION_COOKIE_SAMESITE = "lax"
app.config.SESSION_TIMEOUT = timedelta(hours=24)
app.config.SESSION_REFRESH_THRESHOLD = timedelta(hours=1)

# Login endpoint - creates session
@app.post("/auth/login")
@app.validate(LoginSchema, template="login.html")
async def login(data: LoginSchema, request):
    user = await User.filter(email=data.email).first()
    
    if not user or not user.verify_password(data.password):
        raise ValueError("Invalid email or password")
    
    # Create session
    session = await Session.create(
        user_id=user.id,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else "0.0.0.0",
        expires_at=datetime.now() + timedelta(hours=24)
    )
    
    # Set session cookie
    response = redirect("/dashboard")
    response.set_cookie(
        app.config.SESSION_COOKIE_NAME,
        session.id,
        secure=app.config.SESSION_COOKIE_SECURE,
        httponly=app.config.SESSION_COOKIE_HTTPONLY,
        samesite=app.config.SESSION_COOKIE_SAMESITE,
        max_age=int(app.config.SESSION_TIMEOUT.total_seconds())
    )
    
    return response, {"flash": "Logged in successfully!"}

# Middleware - validates session on each request
@app.middleware("http")
async def session_middleware(request, call_next):
    session_id = request.cookies.get(app.config.SESSION_COOKIE_NAME)
    
    if session_id:
        session = await Session.filter(
            id=session_id,
            expires_at__gt=datetime.now()
        ).first()
        
        if session:
            request.user = await User.get(session.user_id)
            request.session_id = session_id
            
            # Refresh session if close to expiry
            time_until_expiry = session.expires_at - datetime.now()
            if time_until_expiry < app.config.SESSION_REFRESH_THRESHOLD:
                session.expires_at = datetime.now() + app.config.SESSION_TIMEOUT
                await session.save()
        else:
            request.user = None
            response = await call_next(request)
            response.delete_cookie(app.config.SESSION_COOKIE_NAME)
            return response
    
    response = await call_next(request)
    return response

# Logout endpoint - terminates session
@app.post("/auth/logout")
async def logout(request):
    if hasattr(request, 'session_id') and request.session_id:
        session = await Session.get(request.session_id)
        await session.delete()
    
    response = redirect("/")
    response.delete_cookie(app.config.SESSION_COOKIE_NAME)
    return response, {"flash": "Logged out successfully"}
```

### Session Activity Tracking

Track user activity and invalidate inactive sessions:

```python
class ActivityLog(Model):
    user_id: int = f(foreign_key="user.id")
    action: str = f(max_length=255)
    path: str = f(max_length=2048)
    ip_address: str = f(max_length=45)
    created_at: datetime = f(default_factory=datetime.now)

# Track activity
@app.middleware("http")
async def activity_tracking_middleware(request, call_next):
    response = await call_next(request)
    
    if hasattr(request, 'user') and request.user:
        await ActivityLog.create(
            user_id=request.user.id,
            action="page_view",
            path=request.url.path,
            ip_address=request.client.host if request.client else "0.0.0.0"
        )
    
    return response
```

---

## 🔌 Middleware Integration with Request Context

Add user context to every request without passing it manually.

### Custom Auth Middleware

```python
from datetime import datetime
from eden import Eden

app = Eden(__name__)

class AuthMiddleware:
    """Inject user context into requests"""
    
    def __init__(self, app, public_paths=None):
        self.app = app
        self.public_paths = public_paths or [
            "/",
            "/auth/login",
            "/auth/signup",
        ]
    
    async def __call__(self, request, call_next):
        if request.url.path in self.public_paths:
            return await call_next(request)
        
        session_id = request.cookies.get("eden_session")
        
        if session_id:
            session = await Session.filter(
                id=session_id,
                expires_at__gt=datetime.now()
            ).first()
            
            if session:
                request.user = await User.get(session.user_id)
        
        if not hasattr(request, 'user'):
            raise AuthenticationError("Authentication required")
        
        return await call_next(request)

app.add_middleware(AuthMiddleware, public_paths=[
    "/",
    "/auth/login",
    "/auth/signup",
])
```

---

## ✅ Permission Checking Patterns

### Permission Decorators

```python
from functools import wraps

def require_permission(permission: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(request, *args, **kwargs):
            if not request.user or not request.user.has_permission(permission):
                raise PermissionError(f"Missing permission: {permission}")
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

# Usage
@app.post("/posts/{post_id}/publish")
@require_permission("can_publish_posts")
async def publish_post(request, post_id: int):
    post = await Post.get(post_id)
    post.is_published = True
    post.published_at = datetime.now()
    await post.save()
    return json({"published": True})
```

### Permissions in Templates

```html
<!-- Show edit button only if permitted -->
@if(user.has_permission('can_edit_posts')) {
    <a href="@url('posts:edit', id=post.id)" class="btn btn-sm">Edit</a>
}

<!-- Admin-only section -->
@if(user.has_role('admin')) {
    <div class="bg-red-50 p-4 rounded">
        <h3 class="font-bold">🔐 Admin Controls</h3>
        @render_field(form['status'])
        @render_field(form['published_at'])
    </div>
}
```

### Row-Level Security in Queries

```python
async def get_user_posts(user_id: int, current_user: User):
    query = Post.filter(user_id=user_id)
    
    # Admin sees all
    if current_user.has_role("admin"):
        return await query.all()
    
    # Users see their own or published
    if user_id == current_user.id:
        return await query.all()
    
    return await query.filter(is_published=True).all()

@app.get("/users/{user_id}/posts")
async def list_user_posts(request, user_id: int):
    posts = await get_user_posts(user_id, request.user)
    return request.render("user_posts.html", posts=posts)
```

---

## 🎫 Token-Based Authentication (JWT)

For APIs, use JWT tokens instead of session cookies.

### Generate & Validate Tokens

```python
from datetime import datetime, timedelta
import jwt
import os

class TokenAuth:
    SECRET = os.getenv("JWT_SECRET")
    ALGORITHM = "HS256"
    
    @classmethod
    def create_token(cls, user_id: int, expires_in_hours: int = 1) -> str:
        payload = {
            "sub": str(user_id),
            "exp": datetime.utcnow() + timedelta(hours=expires_in_hours),
        }
        return jwt.encode(payload, cls.SECRET, algorithm=cls.ALGORITHM)
    
    @classmethod
    def validate_token(cls, token: str) -> int:
        try:
            payload = jwt.decode(token, cls.SECRET, algorithms=[cls.ALGORITHM])
            return int(payload.get("sub"))
        except jwt.ExpiredSignatureError:
            raise ValueError("Token expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid token")

# API login
@app.post("/api/auth/login")
@app.validate(LoginSchema)
async def api_login(data: LoginSchema, request):
    user = await User.filter(email=data.email).first()
    
    if not user or not user.verify_password(data.password):
        raise ValueError("Invalid credentials")
    
    access_token = TokenAuth.create_token(user.id, expires_in_hours=1)
    refresh_token = TokenAuth.create_token(user.id, expires_in_hours=168)  # 7 days
    
    return json({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 3600
    })

# Protect API routes
@app.middleware("http")
async def api_auth_middleware(request, call_next):
    if request.url.path.startswith("/api/"):
        auth = request.headers.get("authorization", "")
        if not auth.startswith("Bearer "):
            raise AuthenticationError("Missing token")
        
        token = auth[7:]
        try:
            user_id = TokenAuth.validate_token(token)
            request.user = await User.get(user_id)
        except ValueError as e:
            raise AuthenticationError(str(e))
    
    return await call_next(request)
```

---

## 🔄 Password Reset

Secure password reset with email verification:

```python
from secrets import token_urlsafe

class PasswordReset(Model):
    user_id: int = f(foreign_key="user.id")
    token: str = f(max_length=255, unique=True)
    expires_at: datetime = f()
    is_used: bool = f(default=False)

@app.post("/auth/forgot-password")
@app.validate(ForgotPasswordSchema)
async def request_reset(data: ForgotPasswordSchema, request):
    user = await User.filter(email=data.email).first()
    
    if user:
        token = token_urlsafe(32)
        reset = await PasswordReset.create(
            user_id=user.id,
            token=token,
            expires_at=datetime.now() + timedelta(hours=1)
        )
        
        # Send email
        await send_email(
            to=user.email,
            subject="Password Reset",
            template="reset_email",
            context={"link": f"https://yourapp.com/reset?token={token}"}
        )
    
    return json({"message": "Check your email"})

@app.post("/auth/reset-password")
@app.validate(ResetPasswordSchema)
async def reset_password(data: ResetPasswordSchema, request):
    token = request.form.get("token")
    
    reset = await PasswordReset.filter(
        token=token,
        expires_at__gt=datetime.now(),
        is_used=False
    ).first()
    
    if not reset:
        raise ValueError("Invalid token")
    
    user = await User.get(reset.user_id)
    user.password = data.new_password
    await user.save()
    
    reset.is_used = True
    await reset.save()
    
    return redirect("/auth/login", flash="Password reset successful")
```

---

**Next Steps**: [Templating Directives](templating.md)
