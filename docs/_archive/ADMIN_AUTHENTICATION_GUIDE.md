# Admin Dashboard Authentication Guide

Complete guide to adding authentication and authorization to the Eden Admin Dashboard.

## Overview

The authentication system provides:

- ✅ **JWT-based tokens** — Stateless, scalable authentication
- ✅ **Role-based access control (RBAC)** — 3 predefined roles
- ✅ **User management** — Create, update, delete users
- ✅ **Session management** — Track active sessions, logout, forced logout
- ✅ **Login attempts protection** — Lockout after failed attempts
- ✅ **Password hashing** — SHA-256 with salt-free design (add salt in production)
- ✅ **FastAPI integration** — Use `Depends()` for endpoint protection

## Quick Start

### 1. Basic Setup (No Auth)

```python
from fastapi import FastAPI
from eden.admin.dashboard_routes import get_admin_routes

app = FastAPI()
app.include_router(get_admin_routes())

# Dashboard at: http://localhost:8000/admin
```

### 2. With Authentication

```python
from fastapi import FastAPI
from eden.admin.auth import AdminAuthManager, AdminRole
from eden.admin.auth_routes import get_protected_admin_routes

app = FastAPI()

# Create auth manager
auth = AdminAuthManager(secret_key="your-secret-key")

# Register users
auth.register_user("admin", "password", AdminRole.ADMIN)
auth.register_user("editor", "password", AdminRole.EDITOR)

# Add protected routes
app.include_router(get_protected_admin_routes(auth))

# Login at: http://localhost:8000/admin/login
# Dashboard at: http://localhost:8000/admin
```

### 3. Quick Setup

```python
from fastapi import FastAPI
from eden.admin.auth_routes import setup_auth

app = FastAPI()

# One-liner: creates auth with default users
setup_auth(app, secret_key="your-secret-key")

# Default users:
# admin:admin (ADMIN role)
# editor:editor (EDITOR role)
# viewer:viewer (VIEWER role)
```

## User Roles

Three predefined roles with different permissions:

### 1. ADMIN
- **Access:** Full access to everything
- **Permissions:**
  - Read all flags ✅
  - Create flags ✅
  - Edit flags ✅
  - Delete flags ✅
  - Manage users ✅
  - View session stats ✅

### 2. EDITOR
- **Access:** Can modify flags but not delete or manage users
- **Permissions:**
  - Read all flags ✅
  - Create flags ✅
  - Edit flags ✅
  - Delete flags ❌
  - Manage users ❌
  - View stats ❌

### 3. VIEWER
- **Access:** Read-only, view flags and metrics
- **Permissions:**
  - Read all flags ✅
  - Create flags ❌
  - Edit flags ❌
  - Delete flags ❌
  - Manage users ❌
  - View stats ❌

## Authentication Endpoints

### Login

```
POST /admin/api/login
Content-Type: application/json

{
  "username": "admin",
  "password": "password"
}
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "Bearer",
  "user": {
    "username": "admin",
    "role": "admin"
  }
}
```

### Logout

```
POST /admin/api/logout
Authorization: Bearer <token>
```

### Get Current User

```
GET /admin/api/me
Authorization: Bearer <token>
```

Response:
```json
{
  "username": "admin",
  "role": "admin",
  "created_at": "2024-01-15T10:30:00",
  "last_login": "2024-01-16T14:22:00",
  "is_active": true
}
```

## User Management Endpoints

All require ADMIN role.

### List All Users

```
GET /admin/api/users
Authorization: Bearer <admin_token>
```

### Create User

```
POST /admin/api/users?username=alice&password=password&role=editor
Authorization: Bearer <admin_token>
```

Roles: `admin`, `editor`, `viewer`

### Update User Role

```
PATCH /admin/api/users/{username}/role?role=editor
Authorization: Bearer <admin_token>
```

### Delete User

```
DELETE /admin/api/users/{username}
Authorization: Bearer <admin_token>
```

### Change Password

```
POST /admin/api/users/{username}/password?old_password=old&new_password=new
Authorization: Bearer <user_token>
```

Users can only change their own password (or ADMIN can change anyone's).

## Protecting Endpoints

### Require Authentication

```python
from fastapi import Depends
from eden.admin.auth import AdminAuthManager

auth = AdminAuthManager(secret_key="...")

@app.get("/protected")
async def protected_route(current_user = Depends(auth.verify)):
    return {"message": f"Hello {current_user.username}"}
```

### Require Specific Role

```python
from eden.admin.auth import AdminRole

@app.delete("/admin/flags/{flag_id}")
async def delete_flag(
    flag_id: str,
    current_user = Depends(auth.require_role(AdminRole.ADMIN))
):
    # Only ADMIN can delete flags
    return {"deleted": flag_id}
```

### Multiple Roles

```python
@app.post("/admin/flags")
async def create_flag(
    data: dict,
    current_user = Depends(auth.require_role(AdminRole.ADMIN, AdminRole.EDITOR))
):
    # ADMIN or EDITOR can create flags
    return await panel.create_flag(data)
```

## Token Usage

### Getting Token

1. User logs in at `/admin/login`
2. Frontend gets token from login response
3. Frontend stores token in `localStorage` under key `admin_token`

### Using Token

Include in every request:

```
Authorization: Bearer <token>
```

Example with fetch:

```javascript
const token = localStorage.getItem('admin_token');

const response = await fetch('/admin/api/flags/flags', {
    method: 'GET',
    headers: {
        'Authorization': `Bearer ${token}`
    }
});
```

### Token Expiration

Default: 24 hours

After expiration:
- Token becomes invalid
- User must login again
- Frontend should redirect to `/admin/login`

### Token Refresh

Current implementation: No refresh tokens (login again after expiry)

For production, consider implementing refresh tokens:

```python
auth = AdminAuthManager(
    secret_key="...",
    token_expiry_hours=1,  # Short-lived access tokens
)

# Add refresh endpoint that returns new token
```

## Security Best Practices

### 1. Use Strong Secret Key

```python
import secrets

SECRET_KEY = secrets.token_urlsafe(32)  # 32-byte random key
```

### 2. Load from Environment

```python
import os
from dotenv import load_dotenv

load_dotenv()
SECRET_KEY = os.getenv("ADMIN_SECRET_KEY")
```

### 3. Use HTTPS

```python
from fastapi.middleware import TrustedHostMiddleware

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["example.com"]
)
```

### 4. Add Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/admin/api/login")
@limiter.limit("5/minute")
async def login(request: LoginRequest):
    # Max 5 login attempts per minute
    ...
```

### 5. Improve Password Hashing

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Use instead of SHA-256
password_hash = pwd_context.hash(password)
```

### 6. Add CORS Restrictions

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Specific domain only
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization"],
)
```

## Login Flow Diagram

```
┌──────────────┐
│  Browser     │
└──────┬───────┘
       │
       │ 1. GET /admin/login
       ↓
    (Login form displays)
       │
       │ 2. POST /admin/api/login {username, password}
       ↓
┌─────────────────────────────────────┐
│ Auth Manager                        │
│ ├─ Check if user exists             │
│ ├─ Verify password                  │
│ ├─ Check if active                  │
│ └─ Create JWT token                 │
└──────┬────────────────────────────────┘
       │
       │ 3. Return {access_token, ...}
       ↓
┌─────────────────────────────┐
│ Browser                     │
│ ├─ localStorage.setItem()    │
│ │  ('admin_token', token)   │
│ └─ Redirect to /admin       │
└──────┬──────────────────────┘
       │
       │ 4. GET /admin
       │    Headers: Authorization: Bearer <token>
       ↓
┌───────────────────────────────┐
│ Auth Middleware (verify)      │
│ ├─ Extract token              │
│ ├─ Validate JWT signature      │
│ ├─ Check expiration           │
│ └─ Return user object         │
└──────┬────────────────────────┘
       │
       │ 5. Serve dashboard HTML
       ↓
┌─────────────────────────────┐
│ Browser                     │
│ (Authenticated Dashboard)   │
└─────────────────────────────┘
```

## Session Statistics

Get stats on active sessions (ADMIN only):

```
GET /admin/api/stats
Authorization: Bearer <admin_token>
```

Response:
```json
{
  "total_users": 3,
  "active_sessions": 2,
  "total_sessions": 5,
  "users_by_role": {
    "admin": 1,
    "editor": 1,
    "viewer": 1
  }
}
```

## Troubleshooting

### "Invalid token" on dashboard

**Cause:** Token expired or localStorage key wrong

**Fix:**
```javascript
// Check stored token
console.log(localStorage.getItem('admin_token'));

// Clear and re-login
localStorage.removeItem('admin_token');
window.location.href = '/admin/login';
```

### "Too many failed login attempts"

**Cause:** 5+ failed login attempts in lockout window

**Fix:** Wait 15 minutes (configurable) or contact admin to unlock

### "Missing authorization header"

**Cause:** Frontend not sending token

**Fix:** Ensure fetch includes Authorization header:
```javascript
headers: {
    'Authorization': `Bearer ${token}`
}
```

### Password hashing differences

**Cause:** Using weak SHA-256 instead of bcrypt

**Fix:** Upgrade to bcrypt for production:
```python
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"])
```

## Complete Example

See `eden/admin/example_auth_app.py` for a complete working example.

Run it:

```bash
python -m uvicorn eden.admin.example_auth_app:app --reload
```

Then visit:
- Login: http://localhost:8000/admin/login
- Dashboard: http://localhost:8000/admin
- Docs: http://localhost:8000/docs

Test with default credentials:
- **admin:admin** — Full access
- **editor:editor** — Create/edit flags
- **viewer:viewer** — Read-only

## Architecture

```
┌─────────────────────────────────────┐
│   AdminAuthManager                  │
│ ├─ register_user()                  │
│ ├─ login()                          │
│ ├─ verify_token()                   │
│ ├─ verify() [FastAPI Depends]       │
│ └─ require_role() [FastAPI Depends] │
└────────────┬────────────────────────┘
             │
             ├─ In-memory users dict
             ├─ In-memory sessions dict
             ├─ JWT signing/verification
             └─ Password hashing
```

## Production Checklist

- [ ] Use strong SECRET_KEY from environment
- [ ] Upgrade to bcrypt password hashing
- [ ] Add rate limiting on login endpoint
- [ ] Use HTTPS only (disable HTTP)
- [ ] Implement refresh tokens
- [ ] Move users to database
- [ ] Add audit logging for sensitive operations
- [ ] Set up monitoring for failed login attempts
- [ ] Regular security updates
- [ ] Implement 2FA (optional)

---

**For more details:** See source code in `eden/admin/auth.py` and `eden/admin/auth_routes.py`

**Questions?** Check `example_auth_app.py` for complete working setup.
