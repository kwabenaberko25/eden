# Performance Tuning 🚀

Optimize your Eden application for production scale. This guide covers caching, database optimization, and best practices.

---

## Database Query Optimization

### N+1 Query Prevention

Load related data efficiently:

```python
from eden import Model, Router

class User(Model):
    name: str
    email: str

class Post(Model):
    title: str
    user_id: str  # Foreign key

router = Router()

# ❌ SLOW: N+1 problem (1 query + N queries)
@router.get("/posts")
async def list_posts_slow(request):
    posts = await Post.all()
    
    for post in posts:
        # This runs a query for EACH post!
        post.user = await User.get(post.user_id)
    
    return json({"posts": posts})  # N+1 queries total

# ✅ FAST: Eager loading (1 query only)
@router.get("/posts")
async def list_posts_fast(request):
    posts = await Post.all().include("user")  # Eager load
    return json({"posts": posts})
```

### Index Database Columns

Add indexes to frequently queried fields:

```python
from eden import Model
from sqlalchemy import Index

class User(Model):
    email: str
    created_at: datetime
    is_active: bool
    
    # ✅ Index on frequently queried columns
    __table_args__ = (
        Index("idx_email", "email"),  # For lookups
        Index("idx_active_created", "is_active", "created_at"),  # Composite
    )

class Post(Model):
    user_id: str
    created_at: datetime
    
    __table_args__ = (
        Index("idx_user_id", "user_id"),  # For joins
        Index("idx_created", "created_at"),  # For sorting
    )

# Check indexes in production
@app.get("/admin/db-stats")
@require_role("admin")
async def db_stats(request):
    """Monitor which queries are slow."""
    # Use EXPLAIN ANALYZE to find slow queries
    result = await db.execute("EXPLAIN ANALYZE SELECT ...", params=[...])
    return json({"analysis": result})
```

### Pagination

Load data in chunks:

```python
# ❌ SLOW: Load entire table
@router.get("/users")
async def list_users_slow(request):
    users = await User.all()  # Could be millions!
    return json({"users": users})

# ✅ FAST: Paginate
@router.get("/users")
async def list_users_fast(request):
    page = int(request.query_params.get("page", 1))
    per_page = int(request.query_params.get("per_page", 20))
    
    # Validate limits
    per_page = min(per_page, 100)  # Cap at 100
    
    offset = (page - 1) * per_page
    users = await User.all().offset(offset).limit(per_page)
    
    total = await User.count()
    
    return json({
        "users": users,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page
        }
    })
```

### Connection Pooling

Reuse database connections efficiently:

```python
from eden.db import Database

# ✅ CORRECT: Connection pooling
db = Database(
    url="postgresql://user:pass@localhost/db",
    pool_size=20,  # Keep 20 connections ready
    max_overflow=10,  # Allow 10 more if needed
    pool_timeout=30,  # Wait 30s for available connection
    pool_recycle=3600  # Recycle connections after 1 hour
)
```

---

## Caching Strategy

### Cache Hierarchy

Use multi-level caching:

```python
from eden.cache import InMemoryCache, TenantCacheWrapper
from eden.cache.redis import RedisCache
import os

# Level 1: In-memory (fast, process-local)
# Level 2: Redis (fast, shared across processes)
# Level 3: Database (slow, source of truth)

app = Eden(__name__)

# Production: Redis for shared caching
if os.getenv("ENV") == "production":
    redis = RedisCache(url=os.getenv("REDIS_URL"))
    redis.mount(app)
else:
    # Development: In-memory
    cache = InMemoryCache()
    app.cache = cache

@router.get("/user/{user_id}")
async def get_user(request, user_id: str):
    """Three-level lookup."""
    
    # Level 1: Check local variable (already in scope)
    
    # Level 2: Check distributed cache
    user = await app.cache.get(f"user:{user_id}")
    if user:
        return json({"user": user, "source": "cache"})
    
    # Level 3: Hit database
    user = await User.get(user_id)
    
    # Store in cache for future hits
    await app.cache.set(f"user:{user_id}", user, ttl=3600)
    
    return json({"user": user, "source": "database"})
```

### Cache Invalidation Patterns

Prevent stale data:

```python
# Pattern 1: Time-based (TTL)
async def get_config(request):
    config = await app.cache.get("config")
    if not config:
        config = await load_config_from_db()
        await app.cache.set("config", config, ttl=3600)  # 1 hour
    return config

# Pattern 2: Event-based (invalidate on change)
@router.post("/config")
async def update_config(request):
    data = await request.json()
    
    # Update database
    config = await Config.update(data)
    
    # Invalidate cache
    await app.cache.delete("config")
    
    return json({"config": config})

# Pattern 3: Pattern-based (wildcard)
@router.post("/users/{user_id}")
async def update_user(request, user_id: str):
    data = await request.json()
    
    user = await User.get(user_id).update(data)
    
    # Clear related caches
    await app.cache.clear(pattern=f"user:{user_id}:*")
    await app.cache.clear(pattern="user:list:*")
    
    return json({"user": user})

# Pattern 4: Cache stampede prevention
import asyncio

async def get_expensive_data(request):
    """Prevent cache stampede when TTL expires."""
    lock_key = "lock:expensive_data"
    
    data = await app.cache.get("expensive_data")
    if data:
        return data
    
    # First process gets lock, others wait
    lock = await app.cache.get(lock_key)
    if lock:
        # Wait for other process to compute
        for _ in range(10):
            await asyncio.sleep(0.1)
            data = await app.cache.get("expensive_data")
            if data:
                return data
    
    # Compute and cache
    await app.cache.set(lock_key, True, ttl=5)
    try:
        data = await expensive_computation()
        await app.cache.set("expensive_data", data, ttl=3600)
        return data
    finally:
        await app.cache.delete(lock_key)
```

### Cache Warming

Pre-load cache at startup:

```python
app = Eden(__name__)

@app.on_startup
async def warm_cache():
    """Pre-load frequently accessed data."""
    
    # Warm user settings
    users = await User.all().limit(1000)
    for user in users:
        await app.cache.set(
            f"user:{user.id}:settings",
            user.settings,
            ttl=86400  # 24 hours
        )
    
    # Warm config
    config = await Config.get_current()
    await app.cache.set("config", config, ttl=3600)
    
    logger.info("Cache warming completed")
```

---

## Response Optimization

### Compression

Reduce response size:

```python
from starlette.middleware.gzip import GZIPMiddleware

app = Eden(__name__)

# ✅ Compress responses over 500 bytes
app.add_middleware(GZIPMiddleware, minimum_size=500)

# Clients automatically decompress
@router.get("/data")
async def get_data(request):
    # Response will be gzipped if > 500 bytes
    return json({"data": large_dataset})
```

### Selective Field Loading

Send only needed fields:

```python
# ❌ SLOW: All fields
@router.get("/posts")
async def list_posts_verbose(request):
    posts = await Post.all()
    return json({"posts": posts})  # Large response

# ✅ FAST: Only needed fields
@router.get("/posts")
async def list_posts_minimal(request):
    posts = await Post.all().with_only("id", "title", "created_at")
    return json({"posts": posts})  # Smaller response

# Client can specify fields
@router.get("/users/{user_id}")
async def get_user(request, user_id: str):
    fields = request.query_params.get("fields", "id,name,email").split(",")
    
    user = await User.get(user_id)
    
    # Return only requested fields
    filtered = {field: getattr(user, field) for field in fields}
    return json({"user": filtered})
```

---

## Connection & Resource Limits

### Request Timeouts

Prevent hung requests:

```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import asyncio

class TimeoutMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        try:
            response = await asyncio.wait_for(
                call_next(request),
                timeout=30.0  # 30 second timeout
            )
            return response
        except asyncio.TimeoutError:
            return JSONResponse(
                {"error": "Request timeout"},
                status_code=504
            )

app = Eden(__name__)
app.add_middleware(TimeoutMiddleware)
```

### Connection Limits

Don't overload the database:

```python
# In Database config
db = Database(
    url="postgresql://...",
    pool_size=20,         # Base connections
    max_overflow=10,      # Emergency connections
    pool_pre_ping=True,   # Test connections before use
)

# Per-route limits
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.get("/api/expensive")
@limiter.limit("10/minute")
async def expensive_operation(request):
    """Limited to 10 requests per minute."""
    return json({"result": "..."})
```

---

## Monitoring & Profiling

### Query Logging

Identify slow queries:

```python
import logging
import time

logger = logging.getLogger("eden.db")
logger.setLevel(logging.DEBUG)

class QueryProfiler:
    """Log slow database queries."""
    
    @staticmethod
    def log_query(query, params, duration):
        if duration > 0.1:  # Log queries over 100ms
            logger.warning(
                f"Slow query ({duration:.2f}s): {query}",
                extra={"params": params}
            )

# Usage
@router.get("/posts")
async def list_posts(request):
    start = time.time()
    posts = await Post.all()
    duration = time.time() - start
    
    QueryProfiler.log_query("SELECT * FROM posts", {}, duration)
    return json({"posts": posts})
```

### Performance Metrics

Track application performance:

```python
import time
from eden.telemetry import metrics

@router.get("/user/{user_id}")
async def get_user(request, user_id: str):
    start = time.time()
    
    user = await User.get(user_id)
    
    duration = time.time() - start
    
    # Record metric
    metrics.histogram(
        "user_fetch_duration_ms",
        duration * 1000,
        tags={"path": "/user/{user_id}"}
    )
    
    return json({"user": user})

# View metrics dashboard
@app.get("/metrics")
async def prometheus_metrics(request):
    """Expose metrics for Prometheus."""
    return metrics.export()
```

### Memory Leaks

Watch for memory growth:

```python
import tracemalloc
import logging

logger = logging.getLogger(__name__)
tracemalloc.start()

@app.middleware("http")
async def memory_monitor(request, call_next):
    current, peak = tracemalloc.get_traced_memory()
    
    if peak > 1_000_000_000:  # Over 1GB
        logger.warning(f"High memory usage: {peak / 1e9:.2f}GB")
        # Alert ops team
    
    response = await call_next(request)
    return response
```

---

## Production Configuration

### Environment Variables

```bash
# .env.production
DATABASE_URL=postgresql://user:pass@prod-db/db
REDIS_URL=redis://prod-redis:6379
WORKER_PROCESSES=8  # Match CPU cores
MAX_REQUEST_SIZE=5_000_000  # 5MB limit
CACHE_TTL_DEFAULT=3600
ENABLE_PROFILING=false
```

### Load Testing

Before going live:

```bash
# Using Apache Bench
ab -n 10000 -c 100 https://yourapp.com/api/endpoint

# Using wrk (better)
wrk -t8 -c100 -d30s https://yourapp.com/api/endpoint

# Results to check
# - Requests/sec (aim for 1000+)
# - p95 latency (aim for <100ms)
# - p99 latency (aim for <500ms)
```

---

## Performance Checklist

- ✅ Database indexes on frequently queried columns
- ✅ N+1 queries eliminated with eager loading
- ✅ Pagination for large result sets
- ✅ Connection pooling configured
- ✅ Caching strategy implemented (2+ levels)
- ✅ Cache invalidation on updates
- ✅ Response compression enabled
- ✅ Request timeouts configured
- ✅ Slow queries monitored
- ✅ Load tested before production
