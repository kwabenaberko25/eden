"""
Eden — Redis Cache Backend

Provides async Redis caching with a clean API for use in views and middleware.

Usage:
    from eden.cache.redis import RedisCache

    cache = RedisCache(url="redis://localhost:6379")
    await cache.set("key", "value", ttl=300)
    value = await cache.get("key")
"""

from __future__ import annotations

import json
from typing import Any

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None  # type: ignore[assignment]


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
        prefix: str = "eden:",
        default_ttl: int = 300,
    ) -> None:
        if aioredis is None:
            raise ImportError(
                "redis[async] is required. Install it: pip install redis[async]"
            )

        self.url = url
        self.prefix = prefix
        self.default_ttl = default_ttl
        self._client: aioredis.Redis | None = None

    async def connect(self) -> None:
        """Establish connection to Redis."""
        self._client = aioredis.from_url(self.url, decode_responses=True)

    async def disconnect(self) -> None:
        """Close the Redis connection."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _key(self, key: str) -> str:
        """Apply the prefix to a key."""
        return f"{self.prefix}{key}"

    async def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value from cache.

        Returns the deserialized value, or `default` if not found.
        """
        if not self._client:
            await self.connect()

        raw = await self._client.get(self._key(key))
        if raw is None:
            return default

        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """
        Set a value in cache with optional TTL (in seconds).

        Complex objects are JSON-serialized automatically.
        """
        if not self._client:
            await self.connect()

        if isinstance(value, (dict, list, tuple)):
            serialized = json.dumps(value)
        else:
            serialized = str(value)

        ttl = ttl or self.default_ttl
        await self._client.setex(self._key(key), ttl, serialized)

    async def delete(self, key: str) -> None:
        """Delete a key from cache."""
        if not self._client:
            await self.connect()
        await self._client.delete(self._key(key))

    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache."""
        if not self._client:
            await self.connect()
        return bool(await self._client.exists(self._key(key)))

    async def clear(self, pattern: str = "*") -> int:
        """Clear all keys matching the prefix + pattern."""
        if not self._client:
            await self.connect()

        full_pattern = f"{self.prefix}{pattern}"
        keys = []
        async for key in self._client.scan_iter(match=full_pattern):
            keys.append(key)

        if keys:
            return await self._client.delete(*keys)
        return 0

    async def incr(self, key: str, amount: int = 1) -> int:
        """Increment a counter in cache."""
        if not self._client:
            await self.connect()
        return await self._client.incrby(self._key(key), amount)

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
