# Eden Authentication System — Complete Implementation Guide

## Overview

The Eden Framework provides a production-ready, multi-layered authentication and authorization system supporting:

- **User Models** with password hashing, roles, and permissions
- **Password Hashing** using Argon2id (OWASP standard)
- **Query-Level RBAC** for database-level security
- **OAuth 2.0** integration (Google, GitHub)
- **Multiple Auth Backends** (JWT, Sessions, API Keys)
- **Route Protection** via decorators and middleware
- **Role Hierarchies** with permission inheritance

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                   Layer 5: Decorators & Middleware      │
│  @login_required, @roles_required, AuthenticationMW     │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────┴──────────────────────────────────────┐
│        Layer 4: OAuth & Authentication Backends         │
│  JWTBackend, SessionBackend, APIKeyBackend, OAuth2      │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────┴──────────────────────────────────────┐
│         Layer 3: RBAC & Query Filtering                 │
│  EdenRBAC, apply_rbac_filter, user_has_permission       │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────┴──────────────────────────────────────┐
│           Layer 2: Password Hashing                      │
│         hash_password, check_password, Argon2id         │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────┴──────────────────────────────────────┐
│     Layer 1: User Model & Dependencies                  │
│  User, BaseUser, SocialAccount, APIKey                  │
└─────────────────────────────────────────────────────────┘
```

---

## Layer 1: User Model

### BaseUser Mixin

The `BaseUser` mixin provides core user fields and password management:

```python
from eden.auth import User, hash_password

# Create a user
user = User(email="alice@example.com", full_name="Alice Smith")
user.set_password("secure-password-123")
await db.add(user)
await db.commit()

# Verify password
if user.check_password("secure-password-123"):
    print("Login successful")
```

### User Model Fields

| Field | Type | Purpose |
|-------|------|---------|
| `email` | str | Unique email (required) |
| `password_hash` | str | Argon2id hash (cannot be null) |
| `full_name` | str \| None | Display name |
| `is_active` | bool | Account enabled (default: True) |
| `is_staff` | bool | Staff/admin flag (default: False) |
| `is_superuser` | bool | Superuser flag (default: False) |
| `roles` | list[str] | User roles (JSON, default: []) |
| `permissions` | list[str] | Direct permissions (JSON, default: []) |
| `last_login` | str \| None | Last login timestamp |
| `social_accounts` | Relationship | Linked OAuth providers |

### Social Accounts (Multi-Provider Login)

Link OAuth accounts to enable multi-provider login:

```python
from eden.auth import SocialAccount

# When a user logs in via Google
social_account = SocialAccount(
    user_id=user.id,
    provider="google",
    provider_user_id="118234567890",
    provider_metadata={"email": "alice@gmail.com", "picture": "..."}
)
await db.add(social_account)
await db.commit()
```

### API Keys (Programmatic Access)

Generate revocable API keys for CI/CD and integrations:

```python
from eden.auth import APIKey

# Generate a new key
api_key, raw_key = await APIKey.generate(
    session=db,
    user=user,
    name="GitHub Actions CI",
    scopes=["read", "write"],
    expires_at=datetime.datetime.now() + datetime.timedelta(days=365),
)

# raw_key returned once: "eden_a1b2c3d4e5f6..."
# Only the hash is stored in the database

# Use in requests:
# Authorization: Bearer eden_a1b2c3d4e5f6...
# X-API-Key: eden_a1b2c3d4e5f6...
```

---

## Layer 2: Password Hashing

Eden uses **Argon2id** — the winner of the Password Hashing Competition:

```python
from eden.auth import hash_password, check_password, Argon2Hasher

# Hash a password
hashed = hash_password("my-password")
# Result: $argon2id$v=19$m=65540,t=3,p=4$...

# Verify a password
if check_password("my-password", hashed):
    print("Password matches")

# Custom hasher with different parameters
hasher = Argon2Hasher(time_cost=4, memory_cost=131072, parallelism=4)
custom_hash = hasher.hash("password")

# Check if rehash needed (after updating Argon2 parameters)
if hasher.needs_rehash(old_hash):
    new_hash = hasher.hash(password)
```

### Why Argon2id?

- **Memory-hard**: Resistant to GPU/ASIC attacks
- **Time cost**: Configurable delay to prevent brute-force
- **Parallelism**: Multi-threaded hashing
- **OWASP Standard**: Recommended for production systems

---

## Layer 3: Query-Level RBAC

Automatically filter database queries based on user permissions:

```python
from eden.auth import (
    apply_rbac_filter,
    user_has_permission,
    user_has_role,
    user_has_any_permission,
)

# Filter posts by permission
posts_query = Post.select()
filtered = apply_rbac_filter(
    user=request.user,
    query=posts_query,
    required_permission="view_all_posts",  # Bypass owner filter if user has this
    field_name="owner_id"  # Field that stores the owner
)
posts = await filtered.all()

# Direct permission checks
if user_has_permission(user, "delete_users"):
    await user.delete()

# Role checks
if user_has_role(user, "admin"):
    # Admin area

# Any permission
if user_has_any_permission(user, "edit", "delete"):
    # Can edit or delete
```

### RBAC Role Hierarchy

Create role hierarchies with permission inheritance:

```python
from eden.auth import default_rbac

# Define hierarchy: admin > moderator > user
default_rbac.add_role("user")
default_rbac.add_role("moderator", parents=["user"])  # Inherits from user
default_rbac.add_role("admin", parents=["moderator"])  # Inherits from moderator

# Assign permissions
default_rbac.add_permission("user", "read")
default_rbac.add_permission("moderator", "edit")
default_rbac.add_permission("admin", "delete")

# Check permissions
if default_rbac.has_permission(["admin"], "read"):  # True (inherits from user)
    print("Admin can read")

if default_rbac.has_permission(["moderator"], "delete"):  # False
    print("Moderator cannot delete")
```

---

## Layer 4: OAuth Providers

Support multi-provider authentication (Google, GitHub, custom):

```python
from eden.auth import OAuthManager

oauth = OAuthManager()

# Register Google OAuth
oauth.register_google(
    client_id="GOOGLE_CLIENT_ID",
    client_secret="GOOGLE_CLIENT_SECRET",
    scopes=["openid", "email", "profile"],  # Optional override
)

# Register GitHub OAuth
oauth.register_github(
    client_id="GITHUB_CLIENT_ID",
    client_secret="GITHUB_CLIENT_SECRET",
)

# Mount OAuth routes
oauth.mount(app, prefix="/auth/oauth")

# Generated routes:
# GET  /auth/oauth/google/login → Redirects to Google
# GET  /auth/oauth/google/callback → Handles code exchange
# GET  /auth/oauth/github/login → Redirects to GitHub
# GET  /auth/oauth/github/callback → Handles code exchange
```

### OAuth Flow

1. User visits `/auth/oauth/google/login`
2. Redirected to Google auth with state token (CSRF protection)
3. User logs in and authorizes app
4. Redirected to `/auth/oauth/google/callback` with code
5. Backend exchanges code for access token
6. Backend fetches user info from Google
7. Create or link user account
8. Establish session/JWT

### Custom OAuth Handlers

```python
from eden.auth import OAuthProvider

async def handle_google_login(request, user_info):
    """Custom handler for Google OAuth."""
    # user_info contains: id, email, name, picture, ...
    
    from eden.auth import User, SocialAccount
    from eden.responses import RedirectResponse
    
    # Find or create user
    user = await User.get_by_email(request.state.db, user_info["email"])
    if not user:
        user = User(email=user_info["email"], full_name=user_info.get("name"))
        await request.state.db.add(user)
        await request.state.db.commit()
    
    # Link social account
    social = await SocialAccount.get_or_create(
        request.state.db,
        user_id=user.id,
        provider="google",
        provider_user_id=user_info["id"],
    )
    
    # Log in user
    request.session["user_id"] = user.id
    
    return RedirectResponse(url="/dashboard")

oauth.register_google(
    client_id="...",
    client_secret="...",
    on_login=handle_google_login,
)
```

---

## Layer 4: Authentication Backends

### JWT Backend (Stateless)

Perfect for APIs and SPAs:

```python
from eden.auth import JWTBackend

# Configure backend
jwt_backend = JWTBackend(
    secret_key="your-secret-key-here",
    algorithm="HS256",
    access_token_expire_minutes=30,
    refresh_token_expire_days=7,
)

# Create tokens
access_token = jwt_backend.create_access_token({"sub": user.id})
refresh_token = jwt_backend.create_refresh_token({"sub": user.id})

# Returns: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
# Include in request: Authorization: Bearer <token>
```

### Session Backend (Stateful)

Perfect for server-rendered apps:

```python
from eden.auth import SessionBackend

session_backend = SessionBackend()

# On login
await session_backend.login(request, user)
# Sets request.session["_auth_user_id"] = str(user.id)

# On logout
await session_backend.logout(request)
# Clears session
```

### API Key Backend (Persistent)

Perfect for CI/CD and integrations:

```python
from eden.auth import APIKeyBackend

api_key_backend = APIKeyBackend(header_name="X-API-Key")

# Extracts from:
# - Authorization: Bearer eden_a1b2c3d4e5f6...
# - X-API-Key: eden_a1b2c3d4e5f6...

# Hashes the key and looks it up in eden_api_keys table
```

---

## Layer 5: Middleware & Route Protection

### Authentication Middleware

Apply to your app to automatically authenticate requests:

```python
from eden.auth import AuthenticationMiddleware, JWTBackend, SessionBackend

app = Eden()

# Configure backends
jwt_backend = JWTBackend(secret_key="secret")
session_backend = SessionBackend()

# Add middleware
app.add_middleware(
    "auth",
    middleware_class=AuthenticationMiddleware,
    backends=[jwt_backend, session_backend],
)

# Middleware will:
# 1. Try each backend in order
# 2. On success, set request.user
# 3. Store user in context for dependencies
# 4. Cleanup context after response
```

### Decorators

#### @login_required

Ensure user is authenticated:

```python
from eden.auth import login_required
from eden.exceptions import Unauthorized

@app.get("/dashboard")
@login_required
async def dashboard(request):
    return {"message": f"Welcome, {request.user.email}"}
    # Raises Unauthorized if not logged in
```

#### @roles_required

Check for specific roles:

```python
from eden.auth import roles_required

@app.get("/admin")
@roles_required(["admin", "superuser"])
async def admin(request):
    return {"message": "Admin area"}
    # Raises Forbidden if user lacks role
```

#### @permissions_required

Check for specific permissions:

```python
from eden.auth import permissions_required

@app.post("/users/{user_id}/delete")
@permissions_required(["delete_users"])
async def delete_user(request, user_id: int):
    # Requires both "delete_users" permission
    # Raises Forbidden if missing
    user = await User.get(request.state.db, user_id)
    await user.delete()
    return {"message": "User deleted"}
```

#### @require_permission

Single permission with RBAC hierarchy support:

```python
from eden.auth import require_permission

@app.put("/posts/{post_id}")
@require_permission("edit_posts")
async def edit_post(request, post_id: int):
    # Checks: direct permission OR role hierarchy
    # Superusers always allowed
    post = await Post.get(request.state.db, post_id)
    post.content = request.json()["content"]
    await request.state.db.commit()
    return post
```

#### @is_authorized

Alias for login_required:

```python
from eden.auth import is_authorized

@app.get("/profile")
@is_authorized
async def view_profile(request):
    return request.user.dict()
```

#### @bind_user_principal

Bind user to context without requiring authentication:

```python
from eden.auth import bind_user_principal

@app.get("/public")
@bind_user_principal
async def public_view(request):
    # request.user may be None (not required)
    if request.user:
        return {"message": f"Hi {request.user.email}"}
    return {"message": "Hello guest"}
```

---

## Complete Example: Building a Secure API

```python
from eden import Eden
from eden.auth import (
    User,
    JWTBackend,
    APIKeyBackend,
    AuthenticationMiddleware,
    require_permission,
    login_required,
)

app = Eden()

# 1. Configure authentication
jwt_backend = JWTBackend(secret_key="super-secret-key")
api_key_backend = APIKeyBackend()

# 2. Add middleware
app.add_middleware(
    "auth",
    middleware_class=AuthenticationMiddleware,
    backends=[jwt_backend, api_key_backend],
)

# 3. Login endpoint (returns JWT)
@app.post("/auth/login")
async def login(request):
    from eden.auth import hash_password
    
    email = request.json()["email"]
    password = request.json()["password"]
    
    user = await User.query(request.state.db).filter_by(email=email).first()
    if not user or not user.check_password(password):
        raise Unauthorized(detail="Invalid credentials")
    
    # Return JWT tokens
    access_token = jwt_backend.create_access_token({"sub": user.id})
    refresh_token = jwt_backend.create_refresh_token({"sub": user.id})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
    }

# 4. Protected endpoint
@app.get("/users/{user_id}")
@login_required  # Requires authentication
async def get_user(request, user_id: int):
    user = await User.get(request.state.db, user_id)
    if not user:
        raise NotFound(detail="User not found")
    return user

# 5. Admin-only endpoint
@app.delete("/users/{user_id}")
@require_permission("delete_users")  # Requires permission
async def delete_user(request, user_id: int):
    user = await User.get(request.state.db, user_id)
    await user.delete()
    return {"message": "User deleted"}

# 6. Public endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok"}
```

---

## Testing

Comprehensive test suite validates all layers:

```bash
# Run all auth tests
python -m pytest tests/test_auth*.py -v

# Run comprehensive layer tests
python -m pytest tests/test_auth_complete_layers.py -v

# Run specific layer
python -m pytest tests/test_auth_passwords.py -v
python -m pytest tests/test_auth_rbac.py -v
```

---

## Production Checklist

- [ ] Use strong `SECRET_KEY` (32+ character random string)
- [ ] Enable HTTPS/TLS for all auth endpoints
- [ ] Set `access_token_expire_minutes` to 30 or less
- [ ] Use PKCE for OAuth browser-based flows
- [ ] Enable CSRF protection on all state-changing operations
- [ ] Log all authentication failures
- [ ] Monitor for brute-force attacks
- [ ] Implement rate limiting on `/login` endpoints
- [ ] Regularly rotate secrets and API keys
- [ ] Test security policies with OAuth sandboxes
- [ ] Store `SECRET_KEY` in environment, not code
- [ ] Use database transactions for user creation

---

## API Reference

See the `eden.auth` module documentation for complete API reference on all classes and functions.
