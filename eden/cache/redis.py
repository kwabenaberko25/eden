from __future__ import annotations
"""
Eden — Redis Cache Backend

Provides async Redis caching with a clean API for use in views and middleware.

Usage:
    from eden.cache.redis import RedisCache

    cache = RedisCache(url="redis://localhost:6379")
    await cache.set("key", "value", ttl=300)
    value = await cache.get("key")
"""


import json
import asyncio
from typing import Any

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None  # type: ignore[assignment]


# Exception classes
class CacheException(Exception):
    """Base exception for cache-related errors"""
    pass


class CacheKeyError(CacheException):
    """Exception raised when a cache key is not found"""
    pass


class RedisCache:
    """
    Async Redis cache backend for Eden.

    Provides get/set/delete operations with optional TTL and
    automatic JSON serialization for complex values.

    Usage:
        cache = RedisCache(url="redis://localhost:6379/0")
        cache.mount(app)

        # In views:
        await app.cache.set("user:123", {"name": "Alice"}, ttl=600)
        user = await app.cache.get("user:123")
    """

    def __init__(
        self,
        url: str = "redis://localhost:6379/0",
        prefix: str = "",
        default_ttl: int = 3600,
        **kwargs: Any,
    ) -> None:
        if aioredis is None:
            raise ImportError(
                "redis[async] is required. Install it: pip install redis[async]"
            )

        self.host = kwargs.get("host", "localhost")
        self.port = kwargs.get("port", 6379)
        self.db = kwargs.get("db", 0)
        
        if "host" in kwargs or "port" in kwargs:
            self.url = f"redis://{self.host}:{self.port}/{self.db}"
        else:
            self.url = url
            
        self.prefix = prefix
        self.default_ttl = default_ttl
        self.redis: aioredis.Redis | None = None

    async def connect(self) -> None:
        """Establish connection to Redis."""
        try:
            self.redis = aioredis.from_url(self.url, decode_responses=True)
        except Exception as e:
            raise CacheException(f"Failed to connect to Redis: {e}")

    async def disconnect(self) -> None:
        """Close the Redis connection."""
        if self.redis:
            await self.redis.aclose()
            self.redis = None

    def _key(self, key: str) -> str:
        """Apply the prefix to a key."""
        if key.startswith(self.prefix):
            return key
        return f"{self.prefix}{key}"

    async def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value from cache.

        Returns the deserialized value, or `default` if not found.
        """
        try:
            if not self.redis:
                await self.connect()

            raw = await self.redis.get(self._key(key))
            if raw is None:
                return default

            try:
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")
                return json.loads(raw)
            except (json.JSONDecodeError, TypeError, ValueError):
                return raw
        except Exception as e:
            if isinstance(e, (ConnectionError, aioredis.ConnectionError)):
                raise CacheException(f"Redis connection error: {e}")
            raise

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """
        Set a value in cache with optional TTL (in seconds).

        Complex objects are JSON-serialized automatically.
        """
        try:
            if not self.redis:
                await self.connect()

            if isinstance(value, (dict, list, tuple)):
                serialized = json.dumps(value)
            else:
                serialized = str(value)

            ttl = ttl or self.default_ttl
            await self.redis.set(self._key(key), serialized, ex=ttl)
        except Exception as e:
            if isinstance(e, (TypeError, ValueError)):
                raise  # Let serialization errors bubble up as is or wrap if needed
            raise CacheException(f"Redis set error: {e}")

    async def set_many(self, data: dict[str, Any], ttl: int | None = None) -> None:
        """Set multiple values at once."""
        for key, value in data.items():
            await self.set(key, value, ttl=ttl)

    async def get_many(self, keys: list[str]) -> dict[str, Any]:
        """Get multiple values at once."""
        if not self.redis:
            await self.connect()

        prefixed_keys = [self._key(k) for k in keys]
        raw_values = await self.redis.mget(prefixed_keys)
        
        results = {}
        for key, raw in zip(keys, raw_values):
            if raw is None:
                results[key] = None
                continue
                
            try:
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")
                results[key] = json.loads(raw)
            except (json.JSONDecodeError, TypeError, ValueError):
                results[key] = raw
        return results

    async def delete(self, key: str) -> None:
        """Delete a key from cache."""
        try:
            if not self.redis:
                await self.connect()
            await self.redis.delete(self._key(key))
        except Exception as e:
            raise CacheException(f"Redis delete error: {e}")

    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching a pattern."""
        return await self.clear(pattern)

    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache."""
        if not self.redis:
            await self.connect()
        return bool(await self.redis.exists(self._key(key)))

    async def clear(self, pattern: str = "*") -> int:
        """Clear all keys matching the prefix + pattern."""
        if not self.redis:
            await self.connect()

        # Optimization: use flushdb if clearing everything and no prefix
        if pattern == "*" and not self.prefix:
            await self.redis.flushdb()
            return 1 # Return 1 for success

        full_pattern = f"{self.prefix}{pattern}"
        keys = []
        
        # Handle both async iterator (real redis) and list (mock for tests)
        res = self.redis.scan_iter(match=full_pattern)
        if hasattr(res, "__aiter__"):
            async for key in res:
                keys.append(key)
        else:
            # Maybe it's a coroutine returning a list or just a list
            if asyncio.iscoroutine(res):
                res = await res
            for key in res:
                keys.append(key)

        if keys:
            return await self.redis.delete(*keys)
        return 0

    async def incr(self, key: str, amount: int = 1) -> int:
        """Increment a counter in cache."""
        if not self.redis:
            await self.connect()
        return await self.redis.incrby(self._key(key), amount)

    def mount(self, app: Any) -> None:
        """
        Mount this cache backend onto an Eden app.

        Registers startup/shutdown hooks and stores the cache on `app.cache`.
        """
        cache = self

        @app.on_startup
        async def _start_cache():
            await cache.connect()

        @app.on_shutdown
        async def _stop_cache():
            await cache.disconnect()

        app.cache = cache
