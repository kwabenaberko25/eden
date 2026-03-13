# Troubleshooting & FAQ 🔧

Common issues and solutions when developing with Eden.

---

## Installation & Setup

### Q: `ModuleNotFoundError: No module named 'eden'`

**Problem:** Eden not installed or not in Python path.

**Solutions:**

```bash
# 1. Install Eden
pip install eden-framework

# 2. Verify installation
python -c "import eden; print(eden.__version__)"

# 3. Check virtual environment is active
which python  # Should show venv path
# On Windows:
where python  # Should show .venv\Scripts\python.exe
```

### Q: `ImportError: cannot import name 'Eden'`

**Problem:** Importing from wrong module or using old API.

**Solutions:**

```python
# ✅ CORRECT
from eden import Eden

# ❌ WRONG (pre-refactor style)
from eden.app import Eden
```

### Q: `pip install eden-framework` hangs or fails

**Problem:** Network issue, dependency conflict, or slow PyPI mirror.

**Solutions:**

```bash
# 1. Use different PyPI mirror
pip install -i https://mirrors.aliyun.com/pypi/simple/ eden-framework

# 2. Upgrade pip first
pip install --upgrade pip setuptools wheel

# 3. Install without dependencies (debug)
pip install --no-deps eden-framework

# 4. Check network
ping pypi.org
```

---

## Database Issues

### Q: `sqlalchemy.exc.DatabaseError: (psycopg2.OperationalError) could not connect to server`

**Problem:** Database server not running or wrong connection string.

**Solutions:**

```python
# Check connection string
from eden.db import Database

db = Database(
    url="postgresql://user:password@localhost:5432/dbname"
    # Verify all parts:
    # - localhost → correct host?
    # - 5432 → correct port?
    # - dbname → database exists?
    # - user:password → correct credentials?
)

# Test connection
import asyncio

async def test_connection():
    try:
        await db.execute("SELECT 1")
        print("✅ Connection successful")
    except Exception as e:
        print(f"❌ Connection failed: {e}")

asyncio.run(test_connection())
```

**Local PostgreSQL setup:**

```bash
# macOS
brew install postgresql
brew services start postgresql

# Linux
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql

# Windows - Download installer
# https://www.postgresql.org/download/windows/

# Verify running
psql --version
```

### Q: `sqlalchemy.exc.IntegrityError: duplicate key value violates unique constraint`

**Problem:** Duplicate data in unique column.

**Solutions:**

```python
# Check for existing record before creating
user = await User.filter(email=email).first()

if user:
    return {"message": "User already exists"}

# Or use upsert
user = await User.upsert(
    email=email,
    defaults={"name": "John"}
)
```

### Q: `asyncio.TimeoutError: Task was destroyed but it is pending!`

**Problem:** Database connection closes before query completes.

**Solutions:**

```python
# Check connection pool size too small
db = Database(
    url="...",
    pool_size=20,  # Increase from default
    max_overflow=10
)

# Add query timeout
from sqlalchemy import event

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("SET statement_timeout = 30000")  # 30 seconds
```

---

## Authentication Issues

### Q: `Session key not found` - Login doesn't persist

**Problem:** Session middleware not configured or cookies disabled.

**Solutions:**

```python
from eden import Eden
from eden.middleware import SessionMiddleware
import os

app = Eden(__name__)

# ✅ Add session middleware BEFORE routes
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "dev-key-change-in-production")
)

# Verify in route
@app.post("/login")
async def login(request):
    # Set session
    request.session["user_id"] = user.id
    
    # Verify it was set
    print(request.session)  # Should show user_id
    
    return json({"message": "Logged in"})

# Check client cookies
# Browser DevTools → Application → Cookies
# Should see session cookie with httpOnly flag
```

### Q: OAuth callback returns `Invalid state parameter`

**Problem:** State token expired or cross-site attack detected.

**Solutions:**

```python
from eden.auth.oauth import OAuthManager

oauth = OAuthManager()

# State expires in 10 minutes - increase if needed
oauth.register_google(
    client_id="...",
    client_secret="...",
    state_ttl=600  # seconds
)

# Ensure you're using same domain
# Redirect to: https://yourapp.com/auth/oauth/google/callback
# Not: http://localhost:8000/auth/oauth/google/callback (different!)
```

### Q: OAuth returns `Unauthorized client` error

**Problem:** Redirect URI not configured in OAuth provider.

**Solutions:**

```
Google OAuth:
1. Go to Google Cloud Console
2. OAuth 2.0 Client IDs
3. Authorized redirect URIs - Add:
   - https://yourapp.com/auth/oauth/google/callback
   - http://localhost:8000/auth/oauth/google/callback (local dev)
4. Save and wait 1 minute for propagation
```

### Q: Forgot password link expired

**Problem:** Token TTL too short or database record deleted.

**Solutions:**

```python
from eden.auth import generate_password_reset_token

# Increase token lifetime (default 24 hours)
token = generate_password_reset_token(
    user_id=user.id,
    expires_in=86400 * 7  # 7 days
)

# Or extend existing token
@app.post("/auth/resend-reset")
async def resend_reset(request):
    data = await request.json()
    user = await User.get_by(email=data["email"])
    
    # Invalidate old token
    await PasswordResetToken.filter(user=user).delete()
    
    # Create new one
    token = generate_password_reset_token(user.id)
    
    # Send email with link
    await send_email(
        to=user.email,
        template="password_reset",
        context={"link": f"https://yourapp.com/reset/{token}"}
    )
```

---

## Caching Issues

### Q: Cache seems to not work - data is stale

**Problem:** Not checking cache or TTL is too short.

**Solutions:**

```python
from eden.cache import InMemoryCache

cache = InMemoryCache()

# Debug: check if cache has key
exists = await cache.has("user:123")
print(f"Key exists: {exists}")

# Debug: get value with explicit missing check
value = await cache.get("user:123")
print(f"Cached value: {value}")

# Extend TTL
await cache.set("user:123", user_data, ttl=86400)  # Longer TTL

# Check if cache is mounted to app
print(app.cache)  # Should not be None
```

### Q: Redis connection refused

**Problem:** Redis server not running.

**Solutions:**

```bash
# Start Redis locally
# macOS
brew install redis
brew services start redis

# Linux
sudo apt install redis-server
sudo systemctl start redis-server

# Windows - Use WSL
wsl
sudo apt install redis-server
sudo service redis-server start

# Verify running
redis-cli ping  # Should return PONG
```

### Q: `Cannot serialize <object> to JSON`

**Problem:** Cache trying to serialize non-JSON-compatible objects.

**Solutions:**

```python
from eden.cache import RedisCache
from json import JSONEncoder
from datetime import datetime

class EDENEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

cache = RedisCache(
    url="redis://localhost:6379",
    encoder=EDENEncoder
)

# Or convert before caching
user = await User.get(user_id)
await cache.set(
    "user:123",
    user.dict(),  # Convert to dict
    ttl=3600
)
```

---

## Deployment Issues

### Q: App crashes on startup with `No module named eden`

**Problem:** Virtual environment not created in production.

**Solutions:**

```bash
# Production deployment checklist
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Or use Docker
# Dockerfile
FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["eden", "run"]

docker build -t myapp .
docker run -p 8000:8000 myapp
```

### Q: Static files not loading (404 errors)

**Problem:** Static file path not configured.

**Solutions:**

```python
from eden import Eden
from starlette.staticfiles import StaticFiles
import os

app = Eden(__name__)

# Mount static files
app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)

# In template
# <link rel="stylesheet" href="/static/style.css">

# Directory structure
# ├── main.py
# ├── static/
# │   ├── style.css
# │   └── script.js
# └── templates/
#     └── index.html
```

### Q: Environment variables not loading

**Problem:** .env file not in correct location or not loaded.

**Solutions:**

```python
import os
from dotenv import load_dotenv

# Load .env from same directory as script
load_dotenv()

# Or explicit path
load_dotenv("/path/to/.env")

# Verify loaded
print(os.getenv("DATABASE_URL"))  # Should print value

# On production, set via:
# - Heroku: heroku config:set KEY=value
# - Railway: Set via dashboard
# - Docker: ENV variables in Dockerfile or docker-compose.yml
# - Systemd: /etc/environment

# Never commit .env to git
# Add to .gitignore:
# .env
# .env.local
```

---

## API Issues

### Q: CORS error - `Access to XMLHttpRequest has been blocked`

**Problem:** Frontend and backend on different domains.

**Solutions:**

```python
from starlette.middleware.cors import CORSMiddleware

app = Eden(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://myapp.com",
        "https://admin.myapp.com",
        "http://localhost:3000"  # For local frontend dev
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

# Frontend must include credentials
// JavaScript
fetch("https://api.myapp.com/data", {
    credentials: "include",  // Send cookies
    headers: {
        "Content-Type": "application/json"
    }
})
```

### Q: 413 Payload Too Large

**Problem:** Request exceeds max size limit.

**Solutions:**

```python
app = Eden(__name__)

# Increase max request size
app = Eden(
    __name__,
    max_request_size=50 * 1024 * 1024  # 50MB
)

# Or configure per route
from starlette.requests import Request

@app.post("/upload")
async def upload(request: Request):
    # Request already limited by app config
    file = await request.form()
    return json({"uploaded": True})
```

### Q: Endpoint returns empty response or `null`

**Problem:** Model not serializing properly or query returned nothing.

**Solutions:**

```python
@app.get("/users/{user_id}")
async def get_user(request, user_id: str):
    user = await User.get(user_id)
    
    # Debug: Check if user exists
    if not user:
        return json({"error": "User not found"}, status=404)
    
    # Convert model to dict
    return json({"user": user.dict()})

# Or use model serialization
class User(Model):
    id: str
    name: str
    
    def dict(self):
        return {
            "id": str(self.id),
            "name": self.name
        }
```

---

## Performance Issues

### Q: Application is slow - requests taking >1s

**Problem:** Could be database, cache, or N+1 queries.

**Solutions:**

```python
import time

@app.middleware("http")
async def log_request_time(request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    
    if duration > 0.5:  # Log slow requests
        print(f"Slow: {request.url.path} took {duration:.2f}s")
    
    response.headers["X-Process-Time"] = str(duration)
    return response

# Profile specific endpoint
@app.get("/slow")
async def slow_endpoint(request):
    import cProfile
    import pstats
    from io import StringIO
    
    pr = cProfile.Profile()
    pr.enable()
    
    # ... your code ...
    
    pr.disable()
    s = StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
    ps.print_stats(10)  # Top 10 functions
    print(s.getvalue())
```

---

## Testing Issues

### Q: Tests fail with `Event loop closed` error

**Problem:** Async fixture cleanup issue.

**Solutions:**

```python
import pytest

# Use pytest-asyncio fixture
@pytest.fixture
async def client():
    app = create_test_app()
    async with AsyncClient(app=app, base_url="http://test") as async_client:
        yield async_client

# Proper async test
@pytest.mark.asyncio
async def test_user_creation(client):
    response = await client.post("/users", json={
        "name": "John",
        "email": "john@example.com"
    })
    assert response.status_code == 201
```

---

## Quick Debugging Checklist

- ✅ Check stdout/stderr for error messages
- ✅ Verify virtual environment is activated (`which python`)
- ✅ Check if external services are running (PostgreSQL, Redis)
- ✅ Verify environment variables are set (`.env` file exists)
- ✅ Look at request/response in browser DevTools
- ✅ Use `print()` or logging to trace execution
- ✅ Check file permissions (especially for local databases)
- ✅ Verify database migrations have run
- ✅ Clear cache and sessions (`Ctrl+Shift+Del` in browser)
- ✅ Restart the application

---

## Getting Help

If you get stuck:

1. **Check logs** - Eden logs detailed error messages
2. **Search documentation** - Most issues are documented
3. **Search GitHub issues** - https://github.com/eden-framework/eden/issues
4. **Ask community** - GitHub Discussions or Discord
5. **Provide minimal reproduction** - Code example that fails reliably
