"""
Eden — Query Result Caching

Integrates caching with QuerySet to automatically cache query results and invalidate
on mutations. Reduces database load for frequently accessed, infrequently updated data.

**Features:**
- Automatic cache key generation from queries
- TTL-based expiration
- Manual cache invalidation
- Cache warming strategies
- Multi-backend support (Redis, in-memory, custom)

**Usage:**

    from eden.db import QuerySetCached
    
    # Cache for 1 hour
    users = await (User.select()
                   .cache(ttl=3600)
                   .all())
    
    # Clear cache on mutation
    user = await User.get(1)
    user.email = "new@example.com"
    await user.save()  # Auto-invalidates User cache
    
    # Manual cache control
    await User.select().cache_clear()
"""

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CacheBackend:
    """
    Base interface for cache backends.
    Implement this to use custom cache stores (Redis, Memcached, etc.)
    """
    
    async def get(self, key: str) -> Optional[Any]:
        """Retrieve value from cache. Returns None if not found or expired."""
        raise NotImplementedError
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Store value in cache. ttl is in seconds."""
        raise NotImplementedError
    
    async def delete(self, key: str) -> None:
        """Remove key from cache."""
        raise NotImplementedError
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern. Returns count of deleted keys."""
        raise NotImplementedError
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        raise NotImplementedError


class InMemoryCache(CacheBackend):
    """
    Simple in-memory cache backend (single-process only).
    Good for development and single-instance deployments.
    NOT suitable for multi-process environments.
    """
    
    def __init__(self):
        self._store: Dict[str, Tuple[Any, Optional[float]]] = {}
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value and check expiration."""
        if key not in self._store:
            return None
        
        value, expires_at = self._store[key]
        
        # Check expiration
        if expires_at is not None and datetime.now().timestamp() > expires_at:
            del self._store[key]
            return None
        
        return value
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Store value with optional TTL."""
        expires_at = None
        if ttl is not None:
            expires_at = (datetime.now() + timedelta(seconds=ttl)).timestamp()
        
        self._store[key] = (value, expires_at)
        logger.debug(f"Cache SET: {key} (ttl={ttl})")
    
    async def delete(self, key: str) -> None:
        """Delete key from cache."""
        if key in self._store:
            del self._store[key]
            logger.debug(f"Cache DEL: {key}")
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern (simple wildcard support)."""
        import fnmatch
        keys_to_delete = [k for k in self._store.keys() if fnmatch.fnmatch(k, pattern)]
        for key in keys_to_delete:
            del self._store[key]
        
        logger.debug(f"Cache CLEAR: {pattern} ({len(keys_to_delete)} keys)")
        return len(keys_to_delete)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists and is not expired."""
        value = await self.get(key)
        return value is not None


class RedisCache(CacheBackend):
    """
    Redis-backed cache for distributed systems.
    Requires: pip install redis
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0", **kwargs: Any):
        """
        Initialize Redis cache backend.
        
        Args:
            redis_url: Redis connection URL
            **kwargs: Additional parameters for redis.from_url (host, port, db, etc.)
        """
        try:
            import redis.asyncio as redis
        except ImportError:
            raise ImportError(
                "RedisCache requires redis package. "
                "Install with: pip install redis"
            )
        
        # If host/port provided in kwargs, we can build/override the URL
        if "host" in kwargs or "port" in kwargs:
            host = kwargs.pop("host", "localhost")
            port = kwargs.pop("port", 6379)
            db = kwargs.pop("db", 0)
            redis_url = f"redis://{host}:{port}/{db}"
            
        self.redis = redis.from_url(redis_url, decode_responses=True, **kwargs)
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis."""
        value = await self.redis.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Store value in Redis with optional TTL."""
        try:
            serialized = json.dumps(value) if not isinstance(value, str) else value
        except (TypeError, ValueError):
            serialized = str(value)
        
        await self.redis.setex(key, ttl or 3600, serialized)
        logger.debug(f"Cache SET: {key} (ttl={ttl})")
    
    async def delete(self, key: str) -> None:
        """Delete key from Redis."""
        await self.redis.delete(key)
        logger.debug(f"Cache DEL: {key}")
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear keys matching pattern."""
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)
        
        logger.debug(f"Cache CLEAR: {pattern} ({len(keys)} keys)")
        return len(keys)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        return await self.redis.exists(key) > 0
    
    async def close(self) -> None:
        """Close Redis connection."""
        await self.redis.close()


def generate_cache_key(
    model_name: str,
    query_filters: Dict[str, Any] | None = None,
    query_ordering: List[str] | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> str:
    """
    Generate deterministic cache key from query parameters.
    
    Args:
        model_name: Model class name
        query_filters: Dictionary of filter conditions
        query_ordering: List of ordering fields
        limit: Query limit
        offset: Query offset
    
    Returns:
        Deterministic cache key (SHA256 hash)
    
    Example:
        key = generate_cache_key(
            "User",
            {"is_active": True},
            ["name"],
            limit=10,
            offset=0
        )
        # Returns: "user:38ffd4c8a2c42fbe11dd7c8a7e2f44f39ab92ec52fac39e14ce0df0a86a4bdb"
    """
    # Build cache key components
    components = [model_name.lower()]
    
    if query_filters:
        # Sort dict by keys for consistent hashing
        filters_str = json.dumps(query_filters, sort_keys=True, default=str)
        components.append(f"filters:{filters_str}")
    
    if query_ordering:
        components.append(f"order:{','.join(query_ordering)}")
    
    if limit is not None:
        components.append(f"limit:{limit}")
    
    if offset is not None:
        components.append(f"offset:{offset}")
    
    # Hash the components for a clean key
    key_str = "|".join(components)
    hash_digest = hashlib.sha256(key_str.encode()).hexdigest()
    
    return f"{model_name.lower()}:{hash_digest}"


class QueryCache:
    """
    Cache manager for query results.
    Automatically integrated into QuerySet when `.cache()` is called.
    """
    
    _backend: Optional[CacheBackend] = None
    _ttl: int = 3600  # Default 1 hour
    
    @classmethod
    def configure(cls, backend: CacheBackend, ttl: int = 3600) -> None:
        """
        Configure global cache backend.
        
        Args:
            backend: Cache backend instance (InMemoryCache, RedisCache, etc.)
            ttl: Default time-to-live in seconds
        
        Example:
            from eden.db.cache import InMemoryCache, QueryCache
            
            QueryCache.configure(InMemoryCache(), ttl=3600)
        """
        cls._backend = backend
        cls._ttl = ttl
        logger.info(f"Query cache configured: {backend.__class__.__name__} (ttl={ttl}s)")
    
    @classmethod
    async def get(cls, key: str) -> Optional[Any]:
        """Get cached query result."""
        if cls._backend is None:
            return None
        
        return await cls._backend.get(key)
    
    @classmethod
    async def set(cls, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Cache query result."""
        if cls._backend is None:
            return
        
        ttl = ttl or cls._ttl
        await cls._backend.set(key, value, ttl)
    
    @classmethod
    async def delete(cls, key: str) -> None:
        """Invalidate cached result."""
        if cls._backend is None:
            return
        
        await cls._backend.delete(key)
    
    @classmethod
    async def clear_model(cls, model_name: str) -> int:
        """Invalidate all cache entries for a model."""
        if cls._backend is None:
            return 0
        
        pattern = f"{model_name.lower()}:*"
        count = await cls._backend.clear_pattern(pattern)
        logger.info(f"Cleared {count} cache entries for {model_name}")
        return count
    
    @classmethod
    async def exists(cls, key: str) -> bool:
        """Check if cache entry exists."""
        if cls._backend is None:
            return False
        
        return await cls._backend.exists(key)
    
    @classmethod
    def is_configured(cls) -> bool:
        """Check if cache backend is configured."""
        return cls._backend is not None
