"""
Eden — Caching Layer

Provides tenant-aware caching with automatic isolation and global namespace support.
"""

from __future__ import annotations
import functools
import time
import os
import logging
from typing import Any, Protocol, runtime_checkable, Optional, Dict, Callable

from eden.tenancy.context import get_current_tenant_id

logger = logging.getLogger(__name__)

@runtime_checkable
class CacheBackend(Protocol):
    """Protocol for cache backends (Redis, In-Memory, etc)."""
    async def get(self, key: str) -> Any: ...
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None: ...
    async def delete(self, key: str) -> None: ...
    async def has(self, key: str) -> bool: ...
    async def clear(self) -> None: ...

class InMemoryCache:
    """Simple in-memory cache backend for development and testing."""
    def __init__(self):
        self._data: Dict[str, tuple[Any, Optional[float]]] = {}

    async def get(self, key: str) -> Any:
        if key not in self._data:
            return None
        
        value, expiry = self._data[key]
        if expiry and time.time() > expiry:
            del self._data[key]
            return None
            
        return value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        if os.environ.get("EDEN_ENV") == "production":
            logger.warning(
                "In-memory cache used in production! "
                "Set REDIS_URL to enable high-performance distributed caching."
            )
        expiry = time.time() + ttl if ttl else None
        self._data[key] = (value, expiry)

    async def delete(self, key: str) -> None:
        self._data.pop(key, None)

    async def has(self, key: str) -> bool:
        return await self.get(key) is not None

    async def clear(self) -> None:
        self._data.clear()

class SecurityError(Exception):
    """Raised when security boundaries are violated."""
    pass

class TenantCacheWrapper:
    """
    Wraps a standard cache backend to provide automatic tenant isolation.
    Prefixes all keys with 'tenant:{id}:' unless bypass_tenancy is True.
    """
    def __init__(self, backend: CacheBackend):
        self._backend = backend

    def _get_isolated_key(self, key: str, bypass_tenancy: bool = False) -> str:
        """Construct the isolated key string."""
        if bypass_tenancy:
            return f"global:{key}"
            
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            raise SecurityError(
                "Attempted tenant-aware cache access without an active tenant context. "
                "Use bypass_tenancy=True for global data."
            )
        return f"tenant:{tenant_id}:{key}"

    async def get(self, key: str, bypass_tenancy: bool = False) -> Any:
        """Retrieve a value from the cache."""
        isolated_key = self._get_isolated_key(key, bypass_tenancy)
        return await self._backend.get(isolated_key)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None, bypass_tenancy: bool = False) -> None:
        """Set a value in the cache."""
        isolated_key = self._get_isolated_key(key, bypass_tenancy)
        await self._backend.set(isolated_key, value, ttl)

    async def delete(self, key: str, bypass_tenancy: bool = False) -> None:
        """Remove a value from the cache."""
        isolated_key = self._get_isolated_key(key, bypass_tenancy)
        await self._backend.delete(isolated_key)

    async def has(self, key: str, bypass_tenancy: bool = False) -> bool:
        """Check if a key exists in the cache."""
        isolated_key = self._get_isolated_key(key, bypass_tenancy)
        return await self._backend.has(isolated_key)

    @property
    def global_cache(self):
        """Helper to access the global namespace directly."""
        return GlobalCacheView(self)

class GlobalCacheView:
    """Syntactic sugar for accessing the global (bypassed) namespace."""
    def __init__(self, wrapper: TenantCacheWrapper):
        self._wrapper = wrapper

    async def get(self, key: str) -> Any:
        return await self._wrapper.get(key, bypass_tenancy=True)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        await self._wrapper.set(key, value, ttl, bypass_tenancy=True)

    async def delete(self, key: str) -> None:
        await self._wrapper.delete(key, bypass_tenancy=True)

    async def has(self, key: str) -> bool:
        return await self._wrapper.has(key, bypass_tenancy=True)


def cache_view(
    ttl: int = 300,
    key_func: Callable[..., str] | None = None,
    vary_on_user: bool = False,
    cache: Any = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator that caches a view's response for the given TTL.
    """
    _default_cache = InMemoryCache()

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            from starlette.responses import Response
            
            request = kwargs.get("request")
            if request is None:
                for arg in args:
                    if hasattr(arg, "url") and hasattr(arg, "headers"):
                        request = arg
                        break

            if request is None:
                return await func(*args, **kwargs)

            app = getattr(request, "app", None)
            _cache = getattr(app, "cache", None) or cache or _default_cache

            if key_func:
                cache_key = key_func(request)
            else:
                path = str(getattr(request, "url", ""))
                cache_key = f"view:{path}"

            if vary_on_user:
                user = getattr(request, "user", None) or getattr(getattr(request, "state", None), "user", None)
                uid = getattr(user, "id", "anon")
                cache_key = f"{cache_key}:user:{uid}"

            try:
                cached = await _cache.get(cache_key)
                if cached:
                    return Response(
                        content=cached["body"],
                        status_code=cached.get("status", 200),
                        headers={"X-Eden-Cache": "HIT", "Content-Type": cached.get("content_type", "text/html")},
                    )
            except Exception:
                pass

            response = await func(*args, **kwargs)

            try:
                if hasattr(response, "body") and getattr(response, "status_code", 200) < 300:
                    content_type = ""
                    if hasattr(response, "headers"):
                        content_type = response.headers.get("content-type", "text/html")
                    await _cache.set(
                        cache_key,
                        {
                            "body": response.body,
                            "status": response.status_code,
                            "content_type": content_type,
                        },
                        ttl=ttl,
                    )
            except Exception:
                pass

            return response

        return wrapper

    return decorator
