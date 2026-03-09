You are tasked with comprehensively fixing, implementing, and enhancing the Eden Framework located at C:\ideas\eden. This is a massive undertaking requiring meticulous attention to detail.

## SECTION A: CRITICAL BUGS - FIX IMMEDIATELY (Blocking Issues)

### A1. Remove Debug Print Statements

**File**: `eden/db/base.py`, lines ~100-120
**Task**: Remove ALL print() statements that leak internal state. Replace with proper logging:

```python
from eden.logging import get_logger
logger = get_logger("orm")
logger.debug("Resolving relationships for %d models", len(models))
A2. Fix Duplicate Method Definitions
File: eden/app.py
- Remove the first run() method around line 111 (the one with **kwargs)
- Remove the first mount_admin() method around line 121
- Keep ONLY the most complete implementations
A3. Fix Dead Code
File: eden/templating.py, line 182
- Remove duplicate return source statement
A4. Fix Admin CSRF Token Access
File: eden/admin/views.py, line ~118
Change from:
csrf_token = request.scope.get("csrf_token", "")
To:
session = request.scope.get("session", {})
csrf_token = session.get("eden_csrf_token", "")
A5. Fix Admin Route Closure Bug
File: eden/admin/__init__.py
Fix late binding in loop by using default arguments:
def make_routes(model_cls, admin_class):
    @router.get(f"/{model_cls.__tablename__}/", name=f"admin_{model_cls.__tablename__}_list")
    async def list_view(request, _model=model_cls, _admin=admin_class):
        return await admin_list_view(request, _model, _admin)
A6. Fix DateTimeField auto_now Bug
File: eden/db/fields.py, lines ~168-176
Change to properly handle both flags:
if auto_now_add:
    kw["server_default"] = func.now()
if auto_now:
    if "server_default" not in kw:
        kw["server_default"] = func.now()
    kw["onupdate"] = func.now()
---
SECTION B: MISSING ORM METHODS - IMPLEMENT COMPLETELY
B1. Add Timestamp Fields to EdenModel
File: eden/db/base.py
Add to the EdenModel class:
from datetime import datetime, timezone as TZ
created_at: Mapped[datetime] = DateTimeField(
    auto_now_add=True, 
    default_factory=lambda: datetime.now(TZ)
)
updated_at: Mapped[datetime] = DateTimeField(
    auto_now=True, 
    default_factory=lambda: datetime.now(TZ)
)
B2. Add to_schema Class Method
File: eden/db/base.py
@classmethod
def to_schema(cls) -> type[BaseModel]:
    """Generate a Pydantic schema from the model."""
    from pydantic import create_model
    fields = {}
    for name, col in cls.__table__.columns.items():
        col_type = col.type.python_type if hasattr(col.type, 'python_type') else str
        default = ... if not col.nullable else None
        fields[name] = (col_type, default)
    return create_model(f"{cls.__name__}Schema", **fields)
B3. Add get_or_404 Method
File: eden/db/base.py
@classmethod
async def get_or_404(cls, session: AsyncSession, id: Any) -> T:
    """Fetch by ID or raise NotFound exception."""
    obj = await cls.get(session, id)
    if obj is None:
        from eden.exceptions import NotFound
        raise NotFound(detail=f"{cls.__name__} with id {id} not found")
    return obj
B4. Add filter_one Class Method
File: eden/db/base.py
@classmethod
async def filter_one(cls, session: AsyncSession | None = None, **kwargs) -> T | None:
    """Filter and return first match or None."""
    return await cls.query(session).filter(**kwargs).first()
B5. Add count Class Method
File: eden/db/base.py
@classmethod
async def count(cls, session: AsyncSession | None = None) -> int:
    """Return total count of records."""
    return await cls.query(session).count()
B6. Add get_or_create Method
File: eden/db/base.py
@classmethod
async def get_or_create(cls, session: AsyncSession, **kwargs) -> tuple[T, bool]:
    """Get existing or create new record."""
    existing = await cls.filter_one(session, **kwargs)
    if existing:
        return existing, False
    new_obj = await cls.create(session, **kwargs)
    return new_obj, True
B7. Add bulk_create Method
File: eden/db/base.py
@classmethod
async def bulk_create(cls, session: AsyncSession, objects: list[dict]) -> list[T]:
    """Bulk create multiple records."""
    instances = [cls(**obj) for obj in objects]
    session.add_all(instances)
    await session.flush()
    return instances
B8. Integrate AccessControl into EdenModel
File: eden/db/base.py
Add optional access control integration:
class EdenModel(Base, AccessControl):
    # ... existing code
  
    @classmethod
    async def get_for_user(cls, session: AsyncSession, user: Any, action: str = "read"):
        """Get filtered queryset based on user permissions."""
        filters = cls.get_security_filters(user, action)
        if filters is True:  # AllowAll
            return cls.query(session)
        elif filters is False:  # DenyAll
            return cls.query(session).filter(cls.id == None)
        return cls.query(session).filter(filters)
---
SECTION C: NEW FEATURE IMPLEMENTATIONS
C1. Implement API Documentation Generation
New File: eden/openapi.py
from dataclasses import dataclass
from typing import Any
@dataclass
class OpenAPIGenerator:
    """Generate OpenAPI 3.0 schema from Eden routes."""
  
    def generate_schema(self, app: "Eden") -> dict[str, Any]:
        schema = {
            "openapi": "3.0.0",
            "info": {
                "title": app.title or "Eden API",
                "version": "1.0.0",
            },
            "paths": {},
            "components": {"schemas": {}, "securitySchemes": {}},
        }
        for route in app.routes:
            # Extract path, methods, params, responses
            pass
        return schema
Add to eden/app.py:
def get_openapi_schema(self) -> dict:
    from eden.openapi import OpenAPIGenerator
    return OpenAPIGenerator().generate_schema(self)
@app.get("/docs")
async def docs():
    from eden.responses import RedirectResponse
    return RedirectResponse("/swagger-ui")
@app.get("/openapi.json")
async def openapi_json():
    return json(self.get_openapi_schema())
C2. Implement OAuth Integration
New File: eden/auth/oauth.py
class OAuthProvider:
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str,
                 authorize_url: str, token_url: str, user_info_url: str, scope: list[str]):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.authorize_url = authorize_url
        self.token_url = token_url
        self.user_info_url = user_info_url
        self.scope = scope
class GoogleOAuth(OAuthProvider):
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        super().__init__(client_id, client_secret, redirect_uri,
            "https://accounts.google.com/o/oauth2/v2/auth",
            "https://oauth2.googleapis.com/token",
            "https://www.googleapis.com/oauth2/v2/userinfo",
            ["openid", "email", "profile"])
class GitHubOAuth(OAuthProvider):
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        super().__init__(client_id, client_secret, redirect_uri,
            "https://github.com/login/oauth/authorize",
            "https://github.com/login/oauth/access_token",
            "https://api.github.com/user",
            ["user:email"])
C3. Implement Internationalization (i18n)
New File: eden/i18n/__init__.py
from pathlib import Path
from typing import Dict, Optional
class I18n:
    def __init__(self, locale_dir: str = "locales", default_locale: str = "en"):
        self.locale_dir = Path(locale_dir)
        self.default_locale = default_locale
        self._translations: Dict[str, Dict[str, str]] = {}
  
    def load_translations(self, locale: str) -> None:
        # Load .json or .po files
        pass
  
    def gettext(self, message: str, locale: Optional[str] = None) -> str:
        locale = locale or self.default_locale
        return self._translations.get(locale, {}).get(message, message)
  
    def ngettext(self, singular: str, plural: str, n: int, locale: Optional[str] = None) -> str:
        locale = locale or self.default_locale
        messages = self._translations.get(locale, {})
        return messages.get(plural if n != 1 else singular, plural if n != 1 else singular)
def gettext(message: str) -> str:
    """Template filter for translations."""
    from eden.context import get_i18n
    i18n = get_i18n()
    return i18n.gettext(message)
C4. Implement WebSocket Support
New File: eden/websocket.py
from starlette.websockets import WebSocket
from typing import Callable, Dict, Set
import asyncio
class WebSocketManager:
    def __init__(self):
        self.connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()
  
    async def connect(self, room: str, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            if room not in self.connections:
                self.connections[room] = set()
            self.connections[room].add(websocket)
  
    async def disconnect(self, room: str, websocket: WebSocket):
        async with self._lock:
            if room in self.connections:
                self.connections[room].discard(websocket)
  
    async def broadcast(self, room: str, message: str):
        if room in self.connections:
            for ws in self.connections[room]:
                await ws.send_text(message)
# Usage in routes:
ws_manager = WebSocketManager()
@app.websocket("/ws/{room}")
async def websocket_endpoint(websocket: WebSocket, room: str):
    await ws_manager.connect(room, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await ws_manager.broadcast(room, data)
    finally:
        await ws_manager.disconnect(room, websocket)
C5. Implement Redis Cache Backend
New File: eden/cache/redis.py
import redis.asyncio as redis
from typing import Any, Optional
class RedisCacheBackend:
    def __init__(self, url: str = "redis://localhost:6379", prefix: str = "eden:"):
        self.redis = redis.from_url(url)
        self.prefix = prefix
  
    async def get(self, key: str) -> Any:
        value = await self.redis.get(f"{self.prefix}{key}")
        if value:
            import pickle
            return pickle.loads(value)
        return None
  
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        import pickle
        serialized = pickle.dumps(value)
        await self.redis.set(f"{self.prefix}{key}", serialized, ex=ttl)
  
    async def delete(self, key: str) -> None:
        await self.redis.delete(f"{self.prefix}{key}")
  
    async def has(self, key: str) -> bool:
        return await self.redis.exists(f"{self.prefix}{key}") > 0
  
    async def clear(self) -> None:
        await self.redis.flushdb()
C6. Implement S3 Storage Backend
New File: eden/storage/s3.py
import boto3
from botocore.config import Config
from typing import Optional
class S3StorageBackend(StorageBackend):
    def __init__(self, bucket: str, region: str = "us-east-1",
                 access_key: Optional[str] = None, secret_key: Optional[str] = None,
                 base_url: Optional[str] = None):
        self.bucket = bucket
        self.base_url = base_url or f"https://{bucket}.s3.{region}.amazonaws.com"
        self.client = boto3.client('s3', region_name=region,
            aws_access_key_id=access_key, aws_secret_access_key=secret_key,
            config=Config(signature_version='s3v4'))
  
    async def save(self, content, name: str = None, folder: str = "") -> str:
        import asyncio
        key = f"{folder}/{name or uuid.uuid4().hex}"
        if hasattr(content, 'read'):
            content = content.read()
        await asyncio.to_thread(self.client.put_object, Bucket=self.bucket, Key=key, Body=content)
        return key
  
    async def delete(self, name: str) -> None:
        import asyncio
        await asyncio.to_thread(self.client.delete_object, Bucket=self.bucket, Key=name)
  
    def url(self, name: str) -> str:
        return f"{self.base_url}/{name}"
---
SECTION D: IMPROVE EXISTING FEATURES
D1. Add Password Reset Flow to Auth
File: eden/auth/models.py
async def send_password_reset(self, request: Request) -> None:
    """Send password reset email."""
    token = self.create_password_reset_token()
    reset_url = f"{request.base_url}reset-password?token={token}"
    # Send email with reset_url
def create_password_reset_token(self) -> str:
    """Generate time-limited password reset token."""
    import secrets
    return secrets.token_urlsafe(32)
D2. Add Role Hierarchy
File: eden/auth/decorators.py
ROLE_HIERARCHY = {
    "superadmin": ["admin", "moderator", "user"],
    "admin": ["moderator", "user"],
    "moderator": ["user"],
    "user": [],
}
def has_role(user, required_role: str) -> bool:
    """Check if user has required role considering hierarchy."""
    if not hasattr(user, 'roles'):
        return False
    user_roles = set(user.roles)
    required_roles = {required_role}
    # Add all roles above required in hierarchy
    for role, inherits in ROLE_HIERARCHY.items():
        if required_role in inherits:
            required_roles.add(role)
    return bool(user_roles & required_roles)
D3. Add Model Validation Hooks
File: eden/db/base.py
async def validate(self) -> list[str]:
    """Override in subclass to add validation. Returns list of error messages."""
    return []
async def full_clean(self, session: AsyncSession) -> None:
    """Validate model instance."""
    errors = await self.validate()
    if errors:
        from eden.exceptions import ValidationError
        raise ValidationError(detail=errors)
    await self._validate_unique_constraints(session)
D4. Add Response Caching Middleware
File: eden/middleware.py
class CacheMiddleware:
    def __init__(self, app, cache_backend, ttl: int = 300):
        self.app = app
        self.cache = cache_backend
        self.ttl = ttl
  
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
    
        request = Request(scope, receive)
    
        # Check cache for GET requests
        if request.method == "GET":
            cache_key = f"response:{request.url.path}:{request.url.query}"
            cached_response = await self.cache.get(cache_key)
            if cached_response:
                # Return cached response
                return
    
        # Process request normally
        # ... (cache response if successful)
D5. Add Scheduling for Background Tasks
File: eden/tasks.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
class EdenScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
  
    def schedule(self, func, trigger: str, **kwargs):
        """Schedule a task to run periodically.
    
        trigger: 'cron', 'interval', or 'date'
        """
        self.scheduler.add_job(func, trigger, **kwargs)
  
    def start(self):
        self.scheduler.start()
  
    def shutdown(self):
        self.scheduler.shutdown()
# Usage:
scheduler = EdenScheduler()
scheduler.schedule(send_daily_emails, 'cron', hour=9, minute=0)
scheduler.start()
---
SECTION E: VERIFICATION
After completing all fixes, verify by running:
python -m pytest tests/ -v
grep -r "print(" eden/ --include="*.py"  # Should find none
FILES TO MODIFY
- eden/db/base.py
- eden/app.py  
- eden/templating.py
- eden/admin/init.py
- eden/admin/views.py
- eden/db/fields.py
FILES TO CREATE
- eden/openapi.py
- eden/auth/oauth.py
- eden/i18n/init.py
- eden/websocket.py
- eden/cache/redis.py
- eden/storage/s3.py
```
