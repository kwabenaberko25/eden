# Multi-Backend Authentication 🔑

Eden's authentication system supports multiple authentication backends that chain together. A single request can be authenticated by token, session cookie, API key, or any custom backend you define. This guide covers building and chaining authentication backends.

> **New to auth?** Start with [Authentication Basics](security.md) first.

---

## Overview

### The Backend Chain

When a request arrives, Eden tries each backend in order until one succeeds:

```
Incoming Request
  ↓
[1] JWT Token Backend?    → Check Authorization header
    ↓ (Failed/not present)
    ↓
[2] Session Backend?      → Check session cookies
    ↓ (Failed/not present)
    ↓
[3] API Key Backend?      → Check X-API-Key header
    ↓ (Failed/not present)
    ↓
[4] Custom Backend?       → Your own logic
    ↓ (All failed)
    ↓
Request.user = None       → Unauthenticated
```

Each backend **independently attempts** authentication. The first to succeed wins.

---

## Built-in Backends

### JWT Token Backend

```python
from eden.auth.backends.jwt import JWTBackend

jwt_backend = JWTBackend(
    secret_key="your-secret-key",
    algorithm="HS256"
)

app.add_middleware("auth", backends=[jwt_backend])
```

**How it works:**
1. Looks for `Authorization: Bearer <token>` header
2. Decodes JWT using your secret key
3. Extracts user ID from token claims
4. Loads user from database

**Example JWT:**
```python
import jwt

token = jwt.encode(
    {"user_id": 123, "username": "alice"},
    "secret-key",
    algorithm="HS256"
)

# Client sends: Authorization: Bearer <token>
```

### Session Backend

```python
from eden.auth.backends.session import SessionBackend

session_backend = SessionBackend()

app.add_middleware("auth", backends=[session_backend])
```

**How it works:**
1. Checks for session cookie (set by SessionMiddleware)
2. Retrieves `_user_id` from session dict
3. Loads user from database

**Example session usage:**
```python
@app.post("/login")
async def login(request):
    request.session["_user_id"] = user.id
    return {"message": "Logged in"}

@app.get("/profile")
async def profile(request):
    # Session backend automatically finds user
    if request.user:
        return {"user": request.user.dict()}
```

### API Key Backend

```python
from eden.auth.backends.api_key import APIKeyBackend

api_key_backend = APIKeyBackend(
    header_name="X-API-Key"
)

app.add_middleware("auth", backends=[api_key_backend])
```

**How it works:**
1. Checks for `X-API-Key` header
2. Looks up API key in `APIKey` model
3. Validates it's not expired
4. Loads associated user

**Creating API keys:**
```python
# Generate key
from eden.auth.models import APIKey
import secrets

key = APIKey.create(
    user_id=user.id,
    key=secrets.token_urlsafe(32),
    name="Mobile App"
)

# Client uses: X-API-Key: <key>
```

---

## Custom Backends

### Creating a Backend

All backends inherit from `AuthBackend`:

```python
from eden.auth.base import AuthBackend
from typing import Optional

class CustomBackend(AuthBackend):
    """Example: OAuth2 token validation backend."""
    
    async def authenticate(self, request) -> Optional[User]:
        """
        Try to authenticate this request.
        
        Return:
            User object if authenticated
            None if not authenticated (chain continues)
        
        Raise:
            Exception to fail fast (chain stops)
        """
        
        # Check for custom header
        token = request.headers.get("X-Custom-Token")
        if not token:
            return None  # Not present, chain continues
        
        try:
            # Validate token somehow
            user_id = await self.validate_token(token)
            
            # Load user from database
            user = await User.get(user_id)
            return user
            
        except ValueError:
            return None  # Invalid token, chain continues
    
    async def validate_token(self, token: str) -> int:
        """Custom validation logic."""
        # Your implementation
        pass
```

### 5-Step Pattern for Custom Backends

**1. Check if the auth method is present**
```python
async def authenticate(self, request):
    token = request.headers.get("X-Token")
    if not token:
        return None  # Not our auth method
```

**2. Parse/extract credentials**
```python
    # Extract from header
    scheme, credential = token.split()
    if scheme.lower() != "bearer":
        return None
```

**3. Validate credentials**
```python
    try:
        # Decode/validate
        payload = jwt.decode(credential, SECRET)
        user_id = payload.get("user_id")
    except Exception:
        return None  # Invalid
```

**4. Load user from database**
```python
    user = await User.get(user_id)
    if not user:
        return None  # User not found
```

**5. Return user or None to chain**
```python
    return user  # Authenticated!
```

### Real Example: Signature-Based Auth

```python
import hmac
import hashlib
from datetime import datetime, timedelta

class SignatureBackend(AuthBackend):
    """Authenticate using HMAC-SHA256 signature."""
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
    
    async def authenticate(self, request):
        # 1. Check for signature header
        sig_header = request.headers.get("X-Signature")
        if not sig_header:
            return None
        
        # 2. Parse signature components
        try:
            user_id_str, timestamp_str, signature = sig_header.split(":")
            user_id = int(user_id_str)
            timestamp = int(timestamp_str)
        except (ValueError, IndexError):
            return None
        
        # 3. Validate timestamp (prevent replay attacks)
        now = int(datetime.now().timestamp())
        if abs(now - timestamp) > 300:  # 5 minute window
            return None
        
        # 4. Verify HMAC signature
        expected_sig = hmac.new(
            self.secret_key.encode(),
            f"{user_id}:{timestamp}".encode(),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_sig):
            return None
        
        # 5. Load and return user
        user = await User.get(user_id)
        return user

# Register backend
sig_backend = SignatureBackend(secret_key="your-key")
app.add_middleware("auth", backends=[sig_backend])
```

### Real Example: OAuth2 Token Backend

```python
import httpx
from typing import Optional

class OAuth2Backend(AuthBackend):
    """Validate external OAuth2 provider tokens."""
    
    def __init__(self, provider_url: str):
        self.provider_url = provider_url
    
    async def authenticate(self, request) -> Optional[User]:
        # 1. Extract token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header[7:]
        
        # 2. Validate against provider
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.provider_url}/validate",
                    json={"access_token": token},
                    timeout=5.0
                )
            
            if response.status_code != 200:
                return None
            
            provider_user = response.json()
        except httpx.RequestError:
            # Provider down - fail open or closed based on your policy
            return None
        
        # 3. Map provider user to local user
        user = await User.find_or_create(
            provider=self.provider_url,
            provider_id=provider_user["id"],
            defaults={
                "username": provider_user["username"],
                "email": provider_user["email"]
            }
        )
        
        return user

# Register
oauth_backend = OAuth2Backend(provider_url="https://auth.example.com")
app.add_middleware("auth", backends=[oauth_backend])
```

---

## Chaining Backends

### Multiple Backends in One App

```python
from eden.auth.backends.jwt import JWTBackend
from eden.auth.backends.session import SessionBackend
from eden.auth.backends.api_key import APIKeyBackend

# Create backends
jwt_backend = JWTBackend(secret_key="...")
session_backend = SessionBackend()
api_key_backend = APIKeyBackend()

# Register in order of preference
app.add_middleware("auth", backends=[
    jwt_backend,         # Try JWT first (fastest)
    session_backend,     # Then session cookies
    api_key_backend,     # Then API keys
])
```

**Request flow:**
- Web browser: Uses session backend
- Mobile app: Uses JWT or API key backend
- Server-to-server: Uses API key backend
- All authenticated by the same middleware!

### Ordered by Performance

```python
# Fast backends first (avoid I/O)
app.add_middleware("auth", backends=[
    jwt_backend,         # JWT is CPU-bound, very fast
    session_backend,     # Session is in-memory, fast
    oauth_backend,       # OAuth requires HTTP call, slower
])
```

### Route-Specific Backend Fallback

```python
class ConditionalBackend(AuthBackend):
    """Pick backend based on route/method."""
    
    async def authenticate(self, request):
        # Public endpoints don't require auth
        if request.url.path.startswith("/public/"):
            return None
        
        # API endpoints require API key or JWT
        if request.url.path.startswith("/api/"):
            return await self.check_api_auth(request)
        
        # Web endpoints use session
        return await self.check_session_auth(request)
    
    async def check_api_auth(self, request):
        # Try JWT or API key
        pass
    
    async def check_session_auth(self, request):
        # Try session
        pass
```

---

## Handling Authentication Failures

### Graceful Degradation

```python
# Missing credentials = unauthenticated (not errored)
@app.get("/public-api")
async def public_endpoint(request):
    if request.user:
        # Personalized response
        return {"data": user_data, "user": request.user.dict()}
    else:
        # Fallback response
        return {"data": public_data}

# vs. Strict protection
@app.get("/protected-api")
async def protected_endpoint(request):
    if not request.user:
        return {"error": "Unauthorized"}, 401
    
    return {"data": request.user.private_data}
```

### Different Responses for Different Backends

```python
class BadRequestWrapper(AuthBackend):
    """Wrap backend to distinguish invalid vs missing."""
    
    def __init__(self, backend: AuthBackend):
        self.backend = backend
    
    async def authenticate(self, request):
        # If backend raises = invalid credentials = error
        # If backend returns None = not present = continue chain
        user = await self.backend.authenticate(request)
        
        # Could add logging here
        if user:
            logger.info(f"Auth success: {user.username}")
        
        return user

# Usage
app.add_middleware("auth", backends=[
    BadRequestWrapper(JWTBackend(...))
])
```

---

## Caching & Performance

### Cache User Lookups

```python
from functools import lru_cache
import time

class CachedBackend(AuthBackend):
    """Cache user lookups to avoid repeated DB queries."""
    
    def __init__(self, base_backend: AuthBackend, ttl: int = 60):
        self.base_backend = base_backend
        self.ttl = ttl
        self._cache = {}
    
    async def authenticate(self, request):
        # First try base backend
        user = await self.base_backend.authenticate(request)
        if not user:
            return None
        
        # Cache the result
        self._cache[user.id] = (user, time.time())
        return user

# Or use Redis
class RedisCachedBackend:
    async def authenticate(self, request):
        token = self.extract_token(request)
        if not token:
            return None
        
        # Check Redis cache first
        cached_user_id = await redis.get(f"token:{token}")
        if cached_user_id:
            return await User.get(cached_user_id)
        
        # Fall back to full validation
        user_id = self.validate_token(token)
        
        # Cache for 1 hour
        await redis.setex(f"token:{token}", 3600, user_id)
        
        return await User.get(user_id)
```

---

## Testing Multiple Backends

### Unit Testing Custom Backends

```python
import pytest

@pytest.fixture
async def auth_backend():
    return SignatureBackend(secret_key="test-key")

@pytest.mark.asyncio
async def test_valid_signature(auth_backend):
    # Create valid signature
    import hmac, hashlib
    from datetime import datetime
    
    user_id = 123
    timestamp = int(datetime.now().timestamp())
    signature = hmac.new(
        "test-key".encode(),
        f"{user_id}:{timestamp}".encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Create mock request
    request = Mock()
    request.headers = {
        "X-Signature": f"{user_id}:{timestamp}:{signature}"
    }
    
    # Mock User model
    User.get = AsyncMock(return_value=User(id=123, username="test"))
    
    # Test
    user = await auth_backend.authenticate(request)
    assert user.id == 123

@pytest.mark.asyncio
async def test_invalid_signature(auth_backend):
    request = Mock()
    request.headers = {"X-Signature": "invalid"}
    
    user = await auth_backend.authenticate(request)
    assert user is None
```

### Integration Testing Backend Chain

```python
@pytest.mark.asyncio
async def test_backend_chain_order(client):
    """Test that JWT backend is tried before session."""
    
    # Create both JWT and session
    token = create_jwt_token(user_id=123)
    session_cookies = {"session": "session_id"}
    
    # JWT should win
    response = client.get(
        "/api/profile",
        headers={"Authorization": f"Bearer {token}"},
        cookies=session_cookies
    )
    
    assert response.status_code == 200
    assert response.json()["user_id"] == 123
```

---

## Advanced Patterns

### Pattern: Multi-Tenant Auth

```python
class TenantAwareBackend(AuthBackend):
    """Validate that user belongs to tenant."""
    
    async def authenticate(self, request):
        # Get tenant from request
        tenant_id = int(request.headers.get("X-Tenant-ID", 0))
        if not tenant_id:
            return None
        
        # Extract user (using another backend)
        user = await self.base_backend.authenticate(request)
        if not user:
            return None
        
        # Verify user's tenant matches
        user_tenant = await user.get_tenant()
        if user_tenant.id != tenant_id:
            return None  # User not in this tenant
        
        return user
```

### Pattern: Role-Based Backend Selection

```python
class RoleSelectiveBackend(AuthBackend):
    """Different auth rules for different roles."""
    
    async def authenticate(self, request):
        # Public role: any valid token
        if self.is_public_route(request):
            return await self.jwt_backend.authenticate(request)
        
        # Admin role: only session (stricter)
        if self.is_admin_route(request):
            user = await self.session_backend.authenticate(request)
            if user and user.role == "admin":
                return user
            return None
        
        # API role: API key only
        if self.is_api_route(request):
            return await self.api_key_backend.authenticate(request)
        
        return None
```

### Pattern: Audit Every Authentication

```python
class AuditingBackend(AuthBackend):
    """Log all authentication attempts."""
    
    async def authenticate(self, request):
        user = await self.wrapped_backend.authenticate(request)
        
        # Log the attempt
        await AuthLog.create(
            endpoint=request.url.path,
            method=request.method,
            user_id=user.id if user else None,
            success=user is not None,
            ip_address=request.client.host,
            timestamp=datetime.now()
        )
        
        return user
```

---

## API Reference

### AuthBackend Interface

```python
class AuthBackend(ABC, Generic[UserType]):
    """Base class for all authentication backends."""
    
    async def authenticate(
        self, 
        request: Request
    ) -> UserType | None:
        """
        Attempt to authenticate the request.
        
        Args:
            request: The incoming request
            
        Returns:
            User object if authenticated
            None if not authenticated (chain continues)
            
        Raises:
            Exception: To halt the authentication chain
        """
```

### Available Backends

```python
JWTBackend(secret_key, algorithm="HS256")
SessionBackend()
APIKeyBackend(header_name="X-API-Key")
```

---

## Next Steps

- [Security Best Practices](security.md#best-practices) - Secure backend implementation
- [Context Variables](context-variables.md) - Access authenticated user anywhere
- [API Authentication](../guides/api.md) - REST API security patterns
- [Testing](../guides/testing.md) - Backend testing strategies
