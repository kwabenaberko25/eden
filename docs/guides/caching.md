# Caching & Performance 🚀

Eden provides a flexible, high-performance caching system to reduce database load and accelerate your application.

---

## Quick Start

### In-Memory Cache (Default)

```python
from eden.cache import cache

# Set a value
await cache.set("user:123", user_data, ttl=3600)

# Get a value
user = await cache.get("user:123")

# Delete
await cache.delete("user:123")

# Clear all
await cache.clear()
```

### Redis Cache (Distributed)

For production or multi-instance deployments:

```bash
pip install redis aioredis
```

```python
from eden.cache import RedisCache

cache = RedisCache(
    url="redis://localhost:6379"
)

# Mount with automatic connect/disconnect hooks
cache.mount(app)

# Now available as app.cache
await app.cache.set("user:123", {"name": "Alice"}, ttl=600)
user = await app.cache.get("user:123")
```

---

## Cache Backends

### InMemoryCache

Perfect for single-instance applications or caching session data.

**Pros:**
- ✅ No external dependencies
- ✅ Sub-millisecond performance
- ✅ Good for development/testing

**Cons:**
- ❌ Data lost on restart
- ❌ Not shared across instances
- ❌ Uses RAM (good for small datasets only)

```python
from eden.cache import InMemoryCache

cache = InMemoryCache()
app.cache = cache

# Now use via app.cache
await app.cache.set("key", "value", ttl=300)
value = await app.cache.get("key")
```

### RedisCache

Distributed caching perfect for scale and persistence.

**Pros:**
- ✅ Shared across multiple servers
- ✅ Survives restarts
- ✅ Can handle massive datasets
- ✅ Sub-millisecond performance at scale

**Cons:**
- ⚠️ Requires Redis server
- ⚠️ Network latency (microseconds)

```python
from eden.cache import RedisCache

cache = RedisCache(
    url=os.getenv("REDIS_URL", "redis://localhost:6379"),
    db=0,
    encoding="utf-8"
)

app.configure_cache(cache)
```

---

## Common Patterns

### Cache Methods Reference

**Core Operations:**

```python
# Check if key exists
exists = await app.cache.has("user:123")  # or .exists() on RedisCache

# Get value (Redis supports default parameter)
value = await app.cache.get("user:123")
value_safe = await app.cache.get("user:123", default={})  # RedisCache only

# Set with TTL
await app.cache.set("key", "value", ttl=3600)

# Delete single key
await app.cache.delete("user:123")

# Clear all or by pattern
await app.cache.clear()  # Clear all
await app.cache.clear(pattern="user:*")  # Clear pattern (Redis only)

# Increment counter (rate limiting, counters) - Redis only
count = await app.cache.incr("requests:user:123", amount=1)
```

### View-Level Caching

Cache entire view responses by time:

```python
from eden.cache import cache_view

@app.get("/blog/posts")
@cache_view(ttl=3600)
async def blog_list(request):
    posts = await Post.all()
    return render_template("blog.html", posts=posts)
```

**With user-specific caching:**

```python
@app.get("/dashboard")
@cache_view(ttl=1800, vary_on_user=True)  # Cache per user
async def dashboard(request):
    user_data = await User.get(id=request.user.id)
    return render_template("dashboard.html", user=user_data)
```

**Invalidate by clearing pattern:**

```python
@app.post("/blog/posts")
async def create_post(request):
    post = await Post.create(...)
    # Invalidate view cache for blog list
    await app.cache.clear(pattern="view:*blog*")
    return json({"id": post.id})
```

### Query Result Caching

Cache database queries:

```python
async def get_user_with_cache(user_id: int):
    cache_key = f"user:{user_id}"
    
    # Try cache first
    user = await cache.get(cache_key)
    if user:
        return user
    
    # Cache miss - query database
    user = await User.get(id=user_id)
    
    # Store in cache for 1 hour
    await cache.set(cache_key, user, ttl=3600)
    return user
```

### Decorator-Based Caching Pattern

Manually cache function results:

```python
async def get_user_cached(user_id: int):
    """Helper pattern for caching function results."""
    cache_key = f"user:{user_id}:data"
    
    # Try cache first
    cached = await app.cache.get(cache_key)
    if cached:
        return cached
    
    # Cache miss - fetch
    user = await User.get(id=user_id)
    data = user.model_dump()
    
    await app.cache.set(cache_key, data, ttl=3600)
    return data

# Usage
user = await get_user_cached(123)
user = await get_user_cached(123)  # From cache
```

### Session & Cookie Caching

Cache session data across requests:

```python
# Store complex object
await cache.set(
    f"session:{request.session.id}:user_prefs",
    {"theme": "dark", "language": "en"},
    ttl=86400  # 24 hours
)

# Retrieve
prefs = await cache.get(f"session:{request.session.id}:user_prefs")
```

### Rate Limiting with Cache

Combine caching with rate limiting:

```python
from eden.cache import cache

async def check_rate_limit(user_id: str, limit: int = 100, period: int = 3600):
    key = f"ratelimit:{user_id}"
    count = await cache.incr(key)
    
    if count == 1:
        await cache.expire(key, period)
    
    return count <= limit

# In route
@app.post("/api/messages")
async def send_message(request):
    if not await check_rate_limit(request.user.id):
        return json({"error": "Rate limit exceeded"}, status=429)
    
    # Process message
    return json({"ok": True})
```

---

## Multi-Tenancy & Caching

When using multi-tenant deployments, cache keys are automatically namespaced by tenant:

```python
from eden.cache import TenantCacheWrapper
from eden.cache.redis import RedisCache

# Automatically prefixes all keys with current tenant ID
redis = RedisCache(url="redis://localhost:6379")
cache = TenantCacheWrapper(redis)

# In your route with tenant context:
@app.get("/data")
async def get_data(request):
    # Automatically uses tenant:123:data as cache key
    await cache.set("data", some_value)
    
    # Different tenants have isolated cache
    return json({"cached": True})
```

**Accessing Global Cache:**

```python
# When TenantCacheWrapper is active, use .global_cache for non-tenant data
await cache.global_cache.set("global_config", config_data)

# Tenant data still isolated
await cache.set("local_data", user_data)  # Scoped to tenant:123
```

@app.get("/data")
async def get_tenant_data(request):
    # Cache key automatically includes tenant context
    await cache.set("data", some_value)
    return json({"cached": True})
```

Cache key isolation:

```
Tenant A:         tenant:123:user_data
Tenant B:         tenant:456:user_data
Global (shared):  global_config
```

---

## Advanced Patterns

### Cache Warming

Pre-populate cache on startup:

```python
async def warm_cache():
    posts = await Post.all()
    for post in posts:
        await cache.set(f"post:{post.id}", post, ttl=86400)

# Run on app startup
@app.on_event("startup")
async def startup():
    await warm_cache()
```

### Cache Stampede Prevention

When multiple requests hit same key simultaneously, fetch once:

```python
import asyncio

async def safe_expensive_query():
    cache_key = "expensive_result"
    
    # Try cache first
    cached = await app.cache.get(cache_key)
    if cached:
        return cached
    
    # Use a separate "lock" key to prevent duplicate work
    lock_key = f"{cache_key}:computing"
    if await app.cache.exists(lock_key):
        # Another request already computing, wait
        await asyncio.sleep(0.5)
        return await app.cache.get(cache_key)
    
    # Set lock
    await app.cache.set(lock_key, "1", ttl=10)
    
    try:
        result = await expensive_db_query()
        await app.cache.set(cache_key, result, ttl=3600)
        return result
    finally:
        await app.cache.delete(lock_key)
```

### Conditional Caching

Cache based on conditions:

```python
async def expensive_data():
    result = await fetch_data()
    
    # Only cache non-sensitive data
    if not result.get('sensitive'):
        await cache.set("data", result, ttl=3600)
    
    return result
```

### Key Patterns for Bulk Invalidation

Use consistent key patterns for grouped invalidation:

```python
# Store related cache keys with prefix pattern
await app.cache.set("blog:post:123", post_data, ttl=3600)
await app.cache.set("blog:post:456", post_data, ttl=3600)
await app.cache.set("blog:list", all_posts, ttl=1800)

# Later, invalidate all blog-related caches
await app.cache.clear(pattern="blog:*")

# Or just posts
await app.cache.clear(pattern="blog:post:*")
```

---

## Monitoring & Debugging

### Cache Statistics

Monitor cache performance:

```python
stats = await cache.stats()
print(f"Hits: {stats['hits']}")
print(f"Misses: {stats['misses']}")
print(f"Hit Rate: {stats['hit_rate']:.2%}")
```

### Enable Debug Logging

```python
import logging

logging.getLogger("eden.cache").setLevel(logging.DEBUG)

# Will log all cache operations
```

### Inspect Cache

```python
# List all keys (in-memory only)
keys = await cache.keys()
print(f"Cached items: {len(keys)}")

# Get key metadata
ttl = await cache.ttl("user:123")
print(f"Expires in {ttl} seconds")
```

---

## Best Practices

### ✅ DO

- Cache expensive computations (database queries, API calls)
- Use TTL to avoid stale data
- Use tags for related data invalidation
- Monitor cache hit rates
- Implement cache warming for critical data
- Use Redis in production for multi-instance apps

### ❌ DON'T

- Cache user-sensitive data (passwords, tokens)
- Set TTL too high (data staleness)
- Cache objects that change frequently
- Forget to invalidate cache when data changes
- Use in-memory cache in distributed systems
- Cache unbounded query results

---

## Configuration

### Environment-Based Setup

```python
import os
from eden.cache import InMemoryCache
from eden.cache.redis import RedisCache

cache_backend = os.getenv("CACHE_BACKEND", "memory")

if cache_backend == "redis":
    cache = RedisCache(url=os.getenv("REDIS_URL"))
    cache.mount(app)
else:
    cache = InMemoryCache()
    app.cache = cache
```

### Docker Compose Example

```yaml
version: '3'
services:
  app:
    image: my-app
    environment:
      CACHE_BACKEND: redis
      REDIS_URL: redis://redis:6379
    depends_on:
      - redis
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

---

## Performance Tips

| Technique | Impact | Complexity |
|-----------|--------|------------|
| Query result caching | 50-90% faster | Low |
| View-level caching | 70-95% faster | Low |
| Cache warming | 85-99% faster | Medium |
| Distributed caching (Redis) | Scales horizontally | Medium |
| Cache compression | Saves 60-80% space | High |

A well-tuned cache can reduce database load by 80-95% and improve response times by 50-200x.

---

**Next Steps**: Configure your preferred cache backend and implement view or query-level caching for your most-accessed data.
