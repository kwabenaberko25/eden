# Security Best Practices 🔒

Eden provides built-in security features. This guide shows how to use them effectively in production.

---

## Authentication & Authorization

### Authentication

For advanced authentication patterns including multi-backend chaining, see [Multi-Backend Authentication](multi-backend-auth.md).

### Enforce HTTPS in Production

Always require HTTPS for authentication flows:

```python
from eden import Eden

app = Eden(__name__)

@app.before_request
async def enforce_https(request):
    """Redirect HTTP to HTTPS in production."""
    if app.config.get("ENV") == "production":
        if request.url.scheme != "https":
            return RedirectResponse(
                url=request.url.replace(scheme="https"),
                status_code=308
            )
```

### OAuth Security Best Practices

Never expose client secrets in frontend code:

```python
# ✅ CORRECT: Secrets in environment variables
from eden.auth.oauth import OAuthManager
import os

oauth = OAuthManager()

oauth.register_google(
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET")  # Never in code!
)

# ✅ CORRECT: OAuth flow on backend
@app.get("/auth/oauth/google/callback")
async def google_callback(request):
    # Backend verifies token signature
    user = await oauth.handle_callback(request, "google")
    return RedirectResponse(url="/dashboard")

# ❌ WRONG: Exposing tokens to frontend
# Don't return raw tokens; use secure session cookies instead
```

**Environment Setup:**

```bash
# .env (never commit this)
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=xxx_secret_key
GITHUB_CLIENT_ID=xxxxx
GITHUB_CLIENT_SECRET=xxxxx
```

### Role-Based Access Control (RBAC)

## Access Control

### Role-Based Access Control (RBAC)

Implement strict permission hierarchies:

```python
from eden import Model, Router
from eden.auth import require_role, require_permission

router = Router()

# Define role hierarchy in config
ROLE_HIERARCHY = {
    'superadmin': ['admin', 'manager', 'user'],
    'admin': ['manager', 'user'],
    'manager': ['user'],
    'user': []
}

# Endpoint accessible only to admins
@router.get("/admin/users")
@require_role("admin")
async def list_all_users(request):
    """Only admins can list all users."""
    users = await User.all()
    return json({"users": users})

# More granular: require specific permission
@router.delete("/users/{user_id}")
@require_permission("delete:users")
async def delete_user(request, user_id):
    """Different from admin role - specific capability."""
    user = await User.get(user_id)
    await user.delete()
    return json({"deleted": True})

# Check permissions in code
@router.get("/data")
async def get_data(request):
    user = request.user
    
    if not user.has_permission("read:data"):
        return json({"error": "Forbidden"}, status=403)
    
    # Safe to return sensitive data
    return json({"data": "..."})
```

### Password Security

Use Eden's built-in password hashing:

```python
from eden.security import hash_password, verify_password

# When creating user
@app.post("/register")
async def register(request):
    data = await request.json()
    
    # ✅ Hash password automatically
    user = await User.create(
        email=data["email"],
        password=data["password"]  # Eden hashes this
    )
    
    return json({"user_id": user.id})

# When verifying login
@app.post("/login")
async def login(request):
    data = await request.json()
    
    user = await User.get_by(email=data["email"])
    
    # ✅ Secure comparison (timing-safe)
    if not verify_password(data["password"], user.password_hash):
        return json({"error": "Invalid credentials"}, status=401)
    
    # Create session
    request.session["user_id"] = user.id
    return json({"user": user})
```

### Multi-Factor Authentication (MFA)

Protect high-value accounts:

```python
from eden.auth import generate_totp_secret, verify_totp

@app.post("/auth/setup-2fa")
async def setup_2fa(request):
    """Generate TOTP secret for user."""
    user = request.user
    
    secret = generate_totp_secret()
    user.totp_secret = secret
    await user.save()
    
    # Return QR code for authenticator app
    return json({
        "secret": secret,
        "qr_code": f"otpauth://totp/MyApp:{user.email}?secret={secret}"
    })

@app.post("/auth/verify-totp")
async def verify_totp_code(request):
    """Verify TOTP code during login."""
    data = await request.json()
    user = await User.get(data["user_id"])
    
    if not verify_totp(data["code"], user.totp_secret):
        return json({"error": "Invalid code"}, status=401)
    
    # MFA passed
    request.session["user_id"] = user.id
    return json({"authenticated": True})
```

---

## Data Protection

### SQL Injection Prevention

Eden's ORM parameterizes all queries automatically:

```python
# ✅ SAFE: ORM parameterizes the query
users = await User.filter(email=user_input).all()

# ❌ NEVER: String concatenation
# users = await db.execute(f"SELECT * FROM users WHERE email='{user_input}'")

# ✅ SAFE: Raw queries use parameters
users = await db.execute(
    "SELECT * FROM users WHERE email = ?",
    params=[user_input]
)
```

### CSRF Protection

Eden includes CSRF protection by default with sophisticated handling for both session-based and session-less forms.

For comprehensive CSRF documentation including token signing, session-less pages, and troubleshooting, see [CSRF Protection & Session-Less Handling](security.md).

**Quick setup:**

```python
from eden.middleware import CSRFProtection

app = Eden(__name__)

# Enable CSRF middleware
app.add_middleware(CSRFProtection)

# In templates, include CSRF token
@app.get("/form")
async def form_page(request):
    csrf_token = request.session.get("csrf_token")
    return html(f"""
        <form method="POST">
            <input type="hidden" name="_csrf_token" value="{csrf_token}">
            <input type="text" name="email">
            <button>Submit</button>
        </form>
    """)

# POST endpoints validate token automatically
@app.post("/update")
async def update(request):
    # CSRF token already verified by middleware
    data = await request.json()
    return json({"updated": True})
```

### Sensitive Data Masking

Never log or expose sensitive information:

```python
import logging
from eden.security import mask_email, mask_card

logger = logging.getLogger(__name__)

@app.post("/payment")
async def process_payment(request):
    data = await request.json()
    card = data["card_number"]
    email = data["email"]
    
    # ✅ Log masked values
    logger.info(f"Payment from {mask_email(email)} card {mask_card(card)}")
    
    # ✅ Return masked to frontend
    return json({
        "card_ending_in": card[-4:],
        "masked_email": mask_email(email)
    })

# Helper functions
def mask_email(email: str) -> str:
    """Convert user@example.com to u***@example.com"""
    parts = email.split("@")
    if len(parts[0]) <= 2:
        return f"{parts[0][0]}***@{parts[1]}"
    return f"{parts[0][0]}***{parts[0][-1]}@{parts[1]}"

def mask_card(card: str) -> str:
    """Convert 1234567812345678 to ****5678"""
    return f"****{card[-4:]}"
```

---

## Template Security

### Built-in Protections

Eden's templating engine includes automatic security hardening:

**1. XSS Prevention (HTML Escaping)**

All user-controlled output is automatically escaped:

```html
<!-- Safe: User input is HTML-escaped -->
@for(item in items) {
  <p>{{ item.title }}</p>  <!-- Special chars escaped: <, >, &, ", ' -->
}

<!-- Safe: @dump directive escapes output -->
@dump(user_input)  <!-- <, >, & converted to HTML entities -->
```

**2. Template Injection Protection**

Eden prevents code injection through template directives:

```html
<!-- Safe: Template Injection Protection -->
@can('edit:posts') {
  <button>Edit</button>
}

<!-- Safe: CSS/JS URLs properly quoted -->
@css('/styles/main.css')  <!-- href="..." prevents attribute injection -->
@js('/scripts/app.js')     <!-- src="..." prevents attribute injection -->
```

**3. Automatic External Link Hardening**

Links with `target="_blank"` automatically get security attributes:

```html
<!-- Input template -->
<a href="https://external.com" target="_blank">Visit</a>

<!-- Rendered output (automatic) -->
<a href="https://external.com" target="_blank" rel="noopener noreferrer">Visit</a>
```

> [!NOTE]
> The `rel="noopener noreferrer"` is automatically added to prevent window hijacking attacks. This protects users from malicious sites that could control your page via `window.opener`.

### Secure Directive Usage

When using Eden directives with user input:

```python
from eden import render_template

@app.post("/search")
async def search(request):
    query = await request.form()  # User input
    # query is automatically escaped in templates
    return render_template("results.html", query=query)
```

```html
<!-- results.html - Safe: query is automatically escaped -->
<h1>Search results for: {{ query }}</h1>

<!-- Safe: Using directives with user data -->
@if(user.role in ['admin', 'moderator']) {
  <button>Moderate</button>
}
```

### Best Practices

```html
<!-- ✅ SAFE: Trust Eden's escaping for user content -->
{{ user.input }}

<!-- ✅ SAFE: Use @role/@can for permissions -->
@role('admin') {
  Sensitive content
}

<!-- ✅ SAFE: Use @csrf in forms -->
<form method="POST">
  @csrf
  <input type="text" name="email">
</form>

<!-- ❌ UNSAFE: Raw HTML concatenation (don't do this) -->
<!-- {{ '<b>Bold</b>' | safe }} -->

<!-- ❌ UNSAFE: Embedding untrusted code -->
<!-- @php($code_from_user) -->
```

---

## API Security

### Rate Limiting

Prevent brute force and DoS attacks:

```python
from eden.cache import InMemoryCache, RedisCache
from eden.middleware import RateLimitMiddleware

app = Eden(__name__)

# Configure rate limiting
cache = RedisCache(url=os.getenv("REDIS_URL"))
cache.mount(app)

@app.middleware("http")
async def rate_limit_middleware(request, call_next):
    """Allow 100 requests per 60 seconds per IP."""
    ip = request.client.host
    key = f"rate_limit:{ip}"
    
    count = await app.cache.incr(key)
    
    if count == 1:
        # First request this minute
        await app.cache.set(key, 1, ttl=60)
    
    if count > 100:
        return json(
            {"error": "Rate limit exceeded"},
            status=429,
            headers={"Retry-After": "60"}
        )
    
    response = await call_next(request)
    response.headers["X-RateLimit-Remaining"] = str(100 - count)
    return response
```

### API Key Authentication

Secure token-based access:

```python
from eden.auth import verify_api_key
from eden.dependencies import Depends

async def verify_api_header(request):
    """Dependency for API key verification."""
    api_key = request.headers.get("X-API-Key")
    
    if not api_key:
        raise Exception("Missing X-API-Key header")
    
    token = await APIKey.get_by(key=api_key)
    if not token or token.revoked:
        raise Exception("Invalid API key")
    
    # Track usage
    token.last_used = datetime.now()
    await token.save()
    
    return token

@app.get("/api/data")
async def api_endpoint(request, api_key = Depends(verify_api_header)):
    """Protected endpoint requiring API key."""
    return json({"data": "sensitive"})
```

**Rotate keys regularly:**

```python
@app.post("/api-keys/rotate")
@require_role("admin")
async def rotate_api_key(request):
    """Generate new API key, revoke old one."""
    old_key = await APIKey.get(request.query_params["key_id"])
    
    new_key = await APIKey.create(
        user=old_key.user,
        key=generate_random_token(32)
    )
    
    old_key.revoked = True
    await old_key.save()
    
    return json({
        "new_key": new_key.key,
        "message": "Old key revoked. Update your client immediately."
    })
```

### CORS Configuration

Restrict cross-origin requests:

```python
from starlette.middleware.cors import CORSMiddleware

app = Eden(__name__)

# ✅ CORRECT: Only allow trusted domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://myapp.com",
        "https://admin.myapp.com"
    ],  # Never use ["*"] in production!
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
    max_age=600  # Preflight cache
)

# ❌ WRONG: Allows all origins
# allow_origins=["*"]
```

---

## Deployment Security

### Environment Secrets

Never commit secrets to version control:

```python
# ✅ CORRECT: Load from environment
import os
from dotenv import load_dotenv

load_dotenv()  # Load from .env locally

DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY")
STRIPE_KEY = os.getenv("STRIPE_SECRET_KEY")

# In production, use:
# - AWS Secrets Manager
# - HashiCorp Vault
# - GitHub Secrets (for CI/CD)
# - Railway/Vercel environment variables
```

**Example .env (NEVER COMMIT):**

```
DATABASE_URL=postgresql://user:pass@localhost/db
SECRET_KEY=your-super-secret-key-change-this
STRIPE_SECRET_KEY=sk_live_xxx
REDIS_URL=redis://localhost:6379
GOOGLE_CLIENT_SECRET=xxx
```

### Dependency Security

Keep dependencies up-to-date:

```bash
# Check for vulnerabilities
pip install safety
safety check

# Or use pip-audit
pip install pip-audit
pip-audit

# Update routinely
pip install --upgrade -r requirements.txt
```

### Database Security

Encrypt sensitive fields:

```python
from eden import Model
from eden.security import encrypt_field

class User(Model):
    email: str
    ssn: str = encrypt_field()  # Encrypted at rest
    credit_card: str = encrypt_field()
    
    # Public fields
    name: str
    created_at: datetime

# Usage
user = await User.create(
    email="user@example.com",
    ssn="123-45-6789",  # Encrypted before storage
    name="John"
)

# Reading returns decrypted value
print(user.ssn)  # "123-45-6789" (only you can read)
```

---

## Monitoring & Auditing

### Security Logging

Log security events for compliance:

```python
import logging
from datetime import datetime

security_logger = logging.getLogger("security")

@app.post("/login")
async def login(request):
    data = await request.json()
    
    user = await User.get_by(email=data["email"])
    
    if not verify_password(data["password"], user.password_hash):
        # ✅ Log failed attempts
        security_logger.warning(
            f"Failed login attempt for {mask_email(user.email)} "
            f"from IP {request.client.host}"
        )
        return json({"error": "Invalid credentials"}, status=401)
    
    # ✅ Log successful authentication
    security_logger.info(
        f"User {user.id} logged in from {request.client.host}"
    )
    
    request.session["user_id"] = user.id
    return json({"user": user})

@app.post("/admin/users/{user_id}")
@require_role("admin")
async def update_user(request, user_id):
    """Audit admin actions."""
    admin = request.user
    target_user = await User.get(user_id)
    
    security_logger.info(
        f"Admin {admin.id} modified user {user_id}",
        extra={"request_data": await request.json()}
    )
    # ... update logic
```

### Suspicious Activity Detection

Alert on unusual behavior:

```python
from eden import Model
from datetime import datetime, timedelta

class LoginAttempt(Model):
    user_id: str
    ip_address: str
    success: bool
    timestamp: datetime

async def detect_suspicious_login(user_id: str, ip: str) -> bool:
    """Check for suspicious activity."""
    
    # Multiple failed attempts in short time
    recent_failures = await LoginAttempt.filter(
        user_id=user_id,
        success=False
    ).filter(
        timestamp__gte=datetime.now() - timedelta(minutes=15)
    ).count()
    
    if recent_failures > 5:
        # Lock account or require 2FA
        await User.get(user_id).update(locked=True)
        security_logger.alert(f"Account {user_id} locked due to suspicious activity")
        return True
    
    # Login from unusual location
    user_logins = await LoginAttempt.filter(
        user_id=user_id,
        success=True
    ).order_by("-timestamp").limit(10)
    
    known_ips = {login.ip_address for login in user_logins}
    
    if ip not in known_ips and len(known_ips) > 0:
        security_logger.warn(f"Login from new IP {ip} for user {user_id}")
        # Could require email confirmation
        return True
    
    return False
```

---

## Multi-Tenancy Security

When implementing multi-tenant applications, ensure data isolation and enforce access controls per tenant:

```python
from eden import Model
from typing import Annotated
from eden.dependencies import Depends

class TenantUser(Model):
    """User can only access their own tenant's data."""
    tenant_id: int
    email: str
    password: str

class TenantResource(Model):
    """Resource is scoped to tenant."""
    tenant_id: int
    name: str
    owner_id: int

async def get_current_tenant(request) -> int:
    """Extract tenant from subdomain or request context."""
    # tenant from request.headers["X-Tenant-ID"]
    # or from subdomain: tenant_id.myapp.com
    return request.state.tenant_id

async def verify_tenant_access(
    resource_id: int,
    tenant_id: Annotated[int, Depends(get_current_tenant)]
):
    """Ensure user only accesses resources in their tenant."""
    resource = await TenantResource.get(resource_id)
    
    if resource.tenant_id != tenant_id:
        raise Exception("Forbidden: Resource not in your tenant")
    
    return resource

@app.get("/resources/{resource_id}")
async def get_resource(
    request,
    resource = Depends(verify_tenant_access)
):
    """User can only access resources in their tenant."""
    return json(resource.to_dict())
```

---

## WebSocket Authentication

Secure WebSocket connections with authentication and authorization:

```python
from eden.auth import verify_token

@app.websocket("/ws/notifications")
async def websocket_notifications(websocket):
    """Real-time notifications with token-based authentication."""
    
    # Extract token from query parameter or header
    token = websocket.query_params.get("token")
    
    if not token:
        await websocket.close(code=4001, reason="Missing authentication token")
        return
    
    try:
        # Verify token and get user
        user = await verify_token(token)
    except Exception as e:
        await websocket.close(code=4003, reason="Invalid token")
        return
    
    # Store user in connection state
    websocket.user = user
    websocket.tenant_id = user.tenant_id
    
    await websocket.accept()
    
    try:
        async for message in websocket.iter_text():
            # Process authenticated WebSocket messages
            await handle_websocket_message(websocket, user, message)
    except Exception as e:
        await websocket.close(code=1011, reason="Server error")

async def handle_websocket_message(websocket, user, message):
    """Handle WebSocket messages with authorization checks."""
    
    data = parse_json(message)
    action = data.get("action")
    
    # Only allow operations the user has permission for
    if action == "get_data" and not user.has_permission("read:data"):
        await websocket.send_json({
            "error": "Unauthorized: Missing read:data permission"
        })
        return
    
    if action == "update_data" and not user.has_permission("write:data"):
        await websocket.send_json({
            "error": "Unauthorized: Missing write:data permission"
        })
        return
    
    # Process the message
    result = await process_action(user, action, data)
    await websocket.send_json(result)
```

---

## Best Practices



- ✅ HTTPS enforced in production
- ✅ Secrets in environment variables (not code)
- ✅ Password hashing implemented
- ✅ CSRF protection enabled
- ✅ SQL injection prevented (ORM used)
- ✅ Rate limiting configured
- ✅ CORS restricted to trusted domains
- ✅ Admin actions logged
- ✅ Suspicious activity monitored
- ✅ Dependencies kept up-to-date
