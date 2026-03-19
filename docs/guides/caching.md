# ⚡ High-Performance Caching & Performance

**Eden provides an industrial-grade, multi-backend caching system designed for extreme scalability, automatic multi-tenant isolation, and sub-millisecond response times.**

---

## 🧠 Conceptual Overview

Eden's caching layer is built on a **Tenant-Aware** architecture. By default, every cache key is automatically namespaced to the current request's tenant, preventing data leakage and ensuring clean isolation in SaaS environments.

### The Caching Lifecycle (Cache-Aside Pattern)

The "Cache-Aside" pattern is the most robust strategy for web applications. Eden makes it seamless to implement logic that prioritizes the cache while falling back to the primary data source on a miss.

```mermaid
graph TD
    A["Incoming Request"] --> B{"Key in Cache?"}
    B --  "YES (Hit)" --> C["Return Cached Result"]
    B --  "NO (Miss)" --> D["Fetch from DB / API"]
    D --> E["Store result in Cache with TTL"]
    E --> F["Return Fresh Result"]
    
    subgraph "Isolation Layer"
        G["TenantCacheWrapper"]
        H["Automatic Namespacing: tenant:{id"}:{key}"]
    end
    
    B -.-> G
    G --> H
```

### Core Philosophy
1.  **Isolation by Default**: Use `TenantCacheWrapper` to ensure Tenant A can never see Tenant B's data—without changing a single line of logic.
2.  **Pluggable Backends**: Swap `InMemoryCache` (dev) for `RedisCache` (prod) via environment variables.
3.  **Syntactic Sugar**: Built-in decorators like `@cache_view` automate the repetitive task of caching common response payloads.

---

## 🏗️ Architecture & Backends

Eden supports multiple backends depending on your infrastructure needs.

| Backend | Logic | Use Case | Performance |
| :--- | :--- | :--- | :--- |
| **`InMemoryCache`** | Dictionary-based | Development, CI/CD, Small datasets. | < 0.1ms |
| **`RedisCache`** | Remote/Distributed | Production, K8s, Webhooks, SaaS. | ~1-5ms |

### 1. The Global vs. Tenant Namespace
A common challenge in SaaS is caching global data (e.g., config) alongside tenant-specific data (e.g., user profiles).

```python
# Access tenant-specific cache (isolated automatically)
await cache.set("user_profile", data) # Saves as 'tenant:123:user_profile'

# Access global cache (shared across all tenants)
await cache.global_cache.set("system_config", data) # Saves as 'global:system_config'
```

---

## 🚀 Quick Start: Multi-Tenant Setup

Configure your caching layer in your `app.py` or bootstrapper.

```python
import os
from eden.cache.redis import RedisCache
from eden.cache import TenantCacheWrapper, InMemoryCache

# 1. Initialize Backend
if os.getenv("REDIS_URL"):
    backend = RedisCache(url=os.getenv("REDIS_URL"))
else:
    backend = InMemoryCache()

# 2. Wrap for Tenancy (Optional but Recommended)
app.cache = TenantCacheWrapper(backend)
```

---

## ⚡ Elite Patterns

### 1. View-Level Caching (`@cache_view`)
Automatically cache entire responses. Eden handles `HX-Target` variations and user-specific variations automatically.

```python
from eden.cache import cache_view

@app.get("/dashboard")
@cache_view(ttl=3600, vary_on_user=True)
async def dashboard(request):
    # This block only runs on cache miss
    data = await fetch_complex_analytics(request.user)
    return render_template("dashboard.html", data=data)
```

### 2. Cache Stampede Prevention (Atomic Locks)
When a high-traffic key expires, 1000 concurrent requests might try to re-compute it. Use a lock to ensure only one worker computes while others wait.

```python
async def get_popular_data():
    cache_key = "popular_stat"
    result = await cache.get(cache_key)
    
    if result is None:
        # Simple lock pattern
        lock_key = f"{cache_key}:lock"
        if await cache.set(lock_key, "1", ttl=5, nx=True):
            try:
                result = await compute_expensive_query()
                await cache.set(cache_key, result, ttl=3600)
            finally:
                await cache.delete(lock_key)
        else:
            # Wait and retry once
            await asyncio.sleep(0.5)
            result = await cache.get(cache_key)
            
    return result
```

### 3. Namespaced Patterns for Bulk Invalidation
Invalidate groups of related keys instantly.

```python
# Invalidate all blog-related cache for the current tenant
await cache.clear(pattern="blog:*")
```

---

## 📄 API Reference

### `CacheBackend` (Protocol)

| Method | Parameters | Return Type | Description |
| :--- | :--- | :--- | :--- |
| `get` | `key: str` | `Any \| None` | Retrieve a value by key. |
| `set` | `key, value, ttl` | `None` | Store a value with optional TTL (seconds). |
| `has` | `key: str` | `bool` | Check if a key exists without retrieving content. |
| `delete`| `key: str` | `None` | Remove a specific key. |
| `clear` | `pattern: str \| None`| `None` | Clear all or matching keys. |

### `TenantCacheWrapper`

| Method | Argument | Description |
| :--- | :--- | :--- |
| `get/set/delete`| `bypass_tenancy: bool`| If `True`, accesses the `global:` namespace instead of `tenant:{id}:`. |
| `.global_cache`| - | Property that returns a `GlobalCacheView` shorthand. |

---

## 💡 Best Practices

1.  **Production Readiness**: Never use `InMemoryCache` in production behind a load balancer (Gunicorn/Uvicorn workers). Use **Redis**.
2.  **Short TTLs for Volatile Data**: Better to have a 60-second TTL on a dashboard than a 24-hour TTL that requires manual purging.
3.  **Pattern Prefixing**: Always use prefixes like `user:`, `product:`, or `view:` to allow for granular `clear(pattern=...)` calls.
4.  **Serialization**: Eden handles JSON serialization automatically for simple types. For complex classes, implement `to_dict()` or use Pydantic `model_dump()`.

---

**Next Steps**: [Multi-Tenant Database Architecture](tenancy.md)
