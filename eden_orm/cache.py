"""
Eden ORM - Query Caching

Redis-backed query result caching with in-memory fallback.
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, List
from hashlib import md5
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CacheBackend(ABC):
    """Abstract cache backend."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: str, ttl: int = 3600) -> bool:
        """Set value in cache."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        pass
    
    @abstractmethod
    async def clear(self) -> bool:
        """Clear all cache."""
        pass


class InMemoryCache(CacheBackend):
    """In-memory cache (default)."""
    
    def __init__(self, max_size: int = 1000):
        self.cache: Dict[str, tuple] = {}  # (value, expiry)
        self.max_size = max_size
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        if key not in self.cache:
            return None
        
        value, expiry = self.cache[key]
        
        if expiry and datetime.now() > expiry:
            del self.cache[key]
            return None
        
        return value
    
    async def set(self, key: str, value: str, ttl: int = 3600) -> bool:
        """Set value in cache."""
        if len(self.cache) >= self.max_size:
            # Remove oldest entry
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        
        expiry = datetime.now() + timedelta(seconds=ttl) if ttl else None
        self.cache[key] = (value, expiry)
        return True
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if key in self.cache:
            del self.cache[key]
            return True
        return False
    
    async def clear(self) -> bool:
        """Clear all cache."""
        self.cache.clear()
        return True


class RedisCache(CacheBackend):
    """Redis-backed cache."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis = None
    
    async def initialize(self):
        """Initialize Redis connection."""
        try:
            import aioredis
            self.redis = await aioredis.create_redis_pool(self.redis_url)
            logger.info("Redis cache connected")
        except ImportError:
            logger.warning("aioredis not installed, falling back to InMemoryCache")
            return False
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}")
            return False
        return True
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        if not self.redis:
            return None
        try:
            value = await self.redis.get(key)
            return value.decode() if value else None
        except Exception:
            return None
    
    async def set(self, key: str, value: str, ttl: int = 3600) -> bool:
        """Set value in cache."""
        if not self.redis:
            return False
        try:
            await self.redis.setex(key, ttl, value)
            return True
        except Exception:
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self.redis:
            return False
        try:
            return await self.redis.delete(key) > 0
        except Exception:
            return False
    
    async def clear(self) -> bool:
        """Clear all cache."""
        if not self.redis:
            return False
        try:
            await self.redis.flushdb()
            return True
        except Exception:
            return False


class QueryCache:
    """Query result caching."""
    
    def __init__(self, backend: Optional[CacheBackend] = None):
        self.backend = backend or InMemoryCache()
        self.enabled = True
        self.ttl = 3600  # Default 1 hour
    
    def generate_key(self, sql: str, params: List[Any]) -> str:
        """Generate cache key from SQL and params."""
        cache_input = f"{sql}:{json.dumps(params, default=str)}"
        return f"query:{md5(cache_input.encode()).hexdigest()}"
    
    async def get(self, sql: str, params: List[Any]) -> Optional[str]:
        """Get cached query result."""
        if not self.enabled:
            return None
        
        key = self.generate_key(sql, params)
        try:
            return await self.backend.get(key)
        except Exception as e:
            logger.warning(f"Cache get failed: {e}")
            return None
    
    async def set(self, sql: str, params: List[Any], value: str, ttl: Optional[int] = None) -> bool:
        """Cache query result."""
        if not self.enabled:
            return False
        
        key = self.generate_key(sql, params)
        try:
            return await self.backend.set(key, value, ttl or self.ttl)
        except Exception as e:
            logger.warning(f"Cache set failed: {e}")
            return False
    
    async def invalidate(self, sql: str, params: List[Any]) -> bool:
        """Invalidate cached query."""
        key = self.generate_key(sql, params)
        try:
            return await self.backend.delete(key)
        except Exception as e:
            logger.warning(f"Cache invalidate failed: {e}")
            return False
    
    async def clear_all(self) -> bool:
        """Clear all cache."""
        try:
            return await self.backend.clear()
        except Exception as e:
            logger.warning(f"Cache clear failed: {e}")
            return False


# Global cache instance
_query_cache: Optional[QueryCache] = None


def get_query_cache() -> QueryCache:
    """Get global query cache instance."""
    global _query_cache
    if _query_cache is None:
        _query_cache = QueryCache()
    return _query_cache


def set_query_cache(cache: QueryCache):
    """Set global query cache instance."""
    global _query_cache
    _query_cache = cache


def enable_caching(enabled: bool = True):
    """Enable/disable query caching."""
    cache = get_query_cache()
    cache.enabled = enabled


def set_cache_ttl(ttl: int):
    """Set default cache TTL in seconds."""
    cache = get_query_cache()
    cache.ttl = ttl
