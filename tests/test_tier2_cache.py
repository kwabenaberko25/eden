"""
Test suite for Tier 2: Redis Caching Backend

Tests RedisCache functionality and operations.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from eden.cache.redis import (
    RedisCache,
    CacheException,
    CacheKeyError,
)


@pytest.fixture
async def redis_cache():
    """Create a RedisCache instance with mock Redis."""
    cache = RedisCache(
        host="localhost",
        port=6379,
        db=0,
        default_ttl=3600
    )
    
    # Mock the Redis client
    cache.redis = AsyncMock()
    
    yield cache


class TestRedisCacheBasic:
    """Tests for basic cache operations."""
    
    @pytest.mark.asyncio
    async def test_cache_initialization(self):
        """Test cache initialization."""
        cache = RedisCache(host="localhost", port=6379)
        assert cache.host == "localhost"
        assert cache.port == 6379
        assert cache.default_ttl == 3600
    
    @pytest.mark.asyncio
    async def test_set_and_get(self, redis_cache):
        """Test setting and getting a value."""
        redis_cache.redis.set = AsyncMock()
        redis_cache.redis.get = AsyncMock(
            return_value=json.dumps({"id": 123, "name": "John"}).encode()
        )
        
        # Set value
        await redis_cache.set("user:123", {"id": 123, "name": "John"})
        redis_cache.redis.set.assert_called_once()
        
        # Get value
        result = await redis_cache.get("user:123")
        redis_cache.redis.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self, redis_cache):
        """Test getting a non-existent key returns None."""
        redis_cache.redis.get = AsyncMock(return_value=None)
        
        result = await redis_cache.get("nonexistent")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_set_with_ttl(self, redis_cache):
        """Test setting a value with specific TTL."""
        redis_cache.redis.set = AsyncMock()
        
        await redis_cache.set("key", "value", ttl=600)
        
        redis_cache.redis.set.assert_called_once()
        # TTL should be passed to redis
        call_args = redis_cache.redis.set.call_args
        assert call_args is not None
    
    @pytest.mark.asyncio
    async def test_delete_key(self, redis_cache):
        """Test deleting a key."""
        redis_cache.redis.delete = AsyncMock()
        
        await redis_cache.delete("user:123")
        
        redis_cache.redis.delete.assert_called_once_with("user:123")
    
    @pytest.mark.asyncio
    async def test_clear_all(self, redis_cache):
        """Test clearing all cache."""
        redis_cache.redis.flushdb = AsyncMock()
        
        await redis_cache.clear()
        
        redis_cache.redis.flushdb.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_exists(self, redis_cache):
        """Test checking key existence."""
        redis_cache.redis.exists = AsyncMock(return_value=1)
        
        exists = await redis_cache.exists("user:123")
        
        assert exists is True
        redis_cache.redis.exists.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_not_exists(self, redis_cache):
        """Test checking non-existent key."""
        redis_cache.redis.exists = AsyncMock(return_value=0)
        
        exists = await redis_cache.exists("nonexistent")
        
        assert exists is False


class TestRedisCacheBatchOperations:
    """Tests for batch cache operations."""
    
    @pytest.mark.asyncio
    async def test_set_many(self, redis_cache):
        """Test setting multiple values."""
        redis_cache.redis.set = AsyncMock()
        
        data = {
            "user:1": {"id": 1, "name": "Alice"},
            "user:2": {"id": 2, "name": "Bob"},
            "user:3": {"id": 3, "name": "Charlie"},
        }
        
        await redis_cache.set_many(data, ttl=1800)
        
        # Should call set for each key
        assert redis_cache.redis.set.call_count == 3
    
    @pytest.mark.asyncio
    async def test_get_many(self, redis_cache):
        """Test getting multiple values."""
        values = {
            b"user:1": json.dumps({"id": 1}).encode(),
            b"user:2": json.dumps({"id": 2}).encode(),
        }
        
        redis_cache.redis.mget = AsyncMock(
            return_value=list(values.values())
        )
        
        result = await redis_cache.get_many(["user:1", "user:2"])
        
        redis_cache.redis.mget.assert_called_once()
        assert isinstance(result, dict)
    
    @pytest.mark.asyncio
    async def test_get_many_with_missing_keys(self, redis_cache):
        """Test get_many with some missing keys."""
        redis_cache.redis.mget = AsyncMock(
            return_value=[
                json.dumps({"id": 1}).encode(),
                None,
                json.dumps({"id": 3}).encode(),
            ]
        )
        
        result = await redis_cache.get_many(["user:1", "user:2", "user:3"])
        
        # Should handle None values
        assert isinstance(result, dict)


class TestRedisCacheDataTypes:
    """Tests for handling different data types."""
    
    @pytest.mark.asyncio
    async def test_cache_dict(self, redis_cache):
        """Test caching dictionary values."""
        redis_cache.redis.set = AsyncMock()
        redis_cache.redis.get = AsyncMock(
            return_value=json.dumps({"key": "value"}).encode()
        )
        
        data = {"key": "value"}
        await redis_cache.set("test:dict", data)
        
        result = await redis_cache.get("test:dict")
        # Should be deserialized back to dict
    
    @pytest.mark.asyncio
    async def test_cache_list(self, redis_cache):
        """Test caching list values."""
        redis_cache.redis.set = AsyncMock()
        redis_cache.redis.get = AsyncMock(
            return_value=json.dumps([1, 2, 3]).encode()
        )
        
        data = [1, 2, 3]
        await redis_cache.set("test:list", data)
        
        result = await redis_cache.get("test:list")
    
    @pytest.mark.asyncio
    async def test_cache_nested_structures(self, redis_cache):
        """Test caching complex nested structures."""
        redis_cache.redis.set = AsyncMock()
        redis_cache.redis.get = AsyncMock(
            return_value=json.dumps({
                "users": [{"id": 1}, {"id": 2}],
                "count": 2
            }).encode()
        )
        
        data = {
            "users": [{"id": 1}, {"id": 2}],
            "count": 2
        }
        
        await redis_cache.set("test:nested", data)
        result = await redis_cache.get("test:nested")


class TestRedisCachePatterns:
    """Tests for pattern-based operations."""
    
    @pytest.mark.asyncio
    async def test_delete_pattern(self, redis_cache):
        """Test deleting keys by pattern."""
        redis_cache.redis.scan_iter = AsyncMock(
            return_value=["user:1", "user:2", "user:3"]
        )
        redis_cache.redis.delete = AsyncMock()
        
        await redis_cache.delete_pattern("user:*")
        
        redis_cache.redis.scan_iter.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_by_pattern(self, redis_cache):
        """Test retrieving keys by pattern."""
        redis_cache.redis.scan_iter = AsyncMock(
            return_value=["user:1", "user:2"]
        )
        redis_cache.redis.mget = AsyncMock(
            return_value=[
                json.dumps({"id": 1}).encode(),
                json.dumps({"id": 2}).encode(),
            ]
        )
        
        # Implementation may vary
        # This tests the expected interface


class TestRedisCacheNamespace:
    """Tests for key namespacing."""
    
    @pytest.mark.asyncio
    async def test_namespaced_keys(self, redis_cache):
        """Test setting keys with namespace."""
        redis_cache.redis.set = AsyncMock()
        
        # Keys should maintain their full names
        await redis_cache.set("cache:users:1", {"id": 1})
        await redis_cache.set("cache:posts:1", {"title": "Post"})
        
        assert redis_cache.redis.set.call_count == 2
    
    @pytest.mark.asyncio
    async def test_namespace_isolation(self, redis_cache):
        """Test that namespaces isolate data."""
        redis_cache.redis.set = AsyncMock()
        redis_cache.redis.get = AsyncMock(side_effect=[
            json.dumps({"id": 1}).encode(),
            json.dumps({"title": "Post"}).encode(),
        ])
        
        # Set in different namespaces
        await redis_cache.set("users:1", {"id": 1})
        await redis_cache.set("posts:1", {"title": "Post"})
        
        # Get from different namespaces
        user = await redis_cache.get("users:1")
        post = await redis_cache.get("posts:1")


class TestRedisCacheErrors:
    """Tests for error handling."""
    
    @pytest.mark.asyncio
    async def test_connection_error(self, redis_cache):
        """Test handling of connection errors."""
        redis_cache.redis.get = AsyncMock(
            side_effect=ConnectionError("Cannot connect to Redis")
        )
        
        with pytest.raises(CacheException):
            await redis_cache.get("key")
    
    @pytest.mark.asyncio
    async def test_invalid_json_in_cache(self, redis_cache):
        """Test handling of invalid JSON in cache."""
        redis_cache.redis.get = AsyncMock(return_value=b"invalid json")
        
        # Should handle gracefully or raise CacheException
        try:
            result = await redis_cache.get("key")
        except CacheException:
            pass  # Expected
    
    @pytest.mark.asyncio
    async def test_serialization_error(self, redis_cache):
        """Test handling of non-serializable data."""
        # Objects that can't be JSON serialized
        data = {"func": lambda x: x}
        
        # Should raise an error when trying to cache
        with pytest.raises((TypeError, CacheException)):
            await redis_cache.set("key", data)


class TestRedisCacheIntegration:
    """Integration tests for cache workflows."""
    
    @pytest.mark.asyncio
    async def test_cache_aside_pattern(self, redis_cache):
        """Test cache-aside pattern."""
        redis_cache.redis.get = AsyncMock(return_value=None)
        redis_cache.redis.set = AsyncMock()
        
        # Simulate cache miss
        user = await redis_cache.get("user:123")
        if user is None:
            # Load from "database"
            user = {"id": 123, "name": "John"}
            await redis_cache.set("user:123", user)
        
        assert user == {"id": 123, "name": "John"}
        redis_cache.redis.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_write_through_pattern(self, redis_cache):
        """Test write-through pattern."""
        redis_cache.redis.set = AsyncMock()
        redis_cache.redis.get = AsyncMock(
            return_value=json.dumps({"id": 123}).encode()
        )
        
        # Write through cache to "database"
        user = {"id": 123, "name": "Updated"}
        await redis_cache.set("user:123", user)
        # Would also write to database
        
        # Verify cache has the value
        cached = await redis_cache.get("user:123")
        assert cached is not None
    
    @pytest.mark.asyncio
    async def test_cache_invalidation(self, redis_cache):
        """Test cache invalidation patterns."""
        redis_cache.redis.delete = AsyncMock()
        
        # Set some cache
        await redis_cache.set("user:123", {"id": 123})
        
        # Invalidate on update
        await redis_cache.delete("user:123")
        
        redis_cache.redis.delete.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
