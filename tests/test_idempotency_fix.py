"""
Tests for IdempotencyManager TTL and locking fixes (Issue #10).

Verifies:
1. Lock acquire/release uses unique identifiers
2. TTL is configurable and applied to saved results
3. Stale lock releases gracefully (warning, no crash)
4. with_idempotency caches results and prevents duplicate execution
5. delete_key and has_result work correctly
6. Concurrent lock prevention works
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from eden.core.idempotency import IdempotencyManager, with_idempotency


class FakeBackend:
    """In-memory fake DistributedBackend for testing."""
    
    def __init__(self):
        self._store = {}
        self._locks = {}
    
    async def connect(self):
        pass
    
    async def disconnect(self):
        pass
    
    async def get(self, key: str):
        return self._store.get(key)
    
    async def set(self, key: str, value, ttl=None):
        self._store[key] = value
        # Record TTL for test assertions
        if ttl is not None:
            self._store[f"_ttl:{key}"] = ttl
    
    async def delete(self, key: str):
        self._store.pop(key, None)
        self._store.pop(f"_ttl:{key}", None)
    
    async def acquire_lock(self, name: str, timeout: float = 10.0, identifier: str = None) -> bool:
        if name in self._locks:
            return False  # Already locked
        self._locks[name] = identifier
        return True
    
    async def release_lock(self, name: str, identifier: str) -> bool:
        if name in self._locks and self._locks[name] == identifier:
            del self._locks[name]
            return True
        return False
    
    async def publish(self, channel, message):
        return 0
    
    async def subscribe(self, channel, callback):
        pass


@pytest.fixture
def backend():
    return FakeBackend()


@pytest.fixture
def manager(backend):
    return IdempotencyManager(backend, default_ttl=3600, lock_timeout=30.0)


class TestIdempotencyLocking:
    """Test that lock acquire/release uses proper identifiers."""
    
    @pytest.mark.asyncio
    async def test_lock_acquires_with_unique_id(self, manager, backend):
        """Each lock acquisition should generate a unique identifier."""
        await manager.acquire_lock("key1")
        
        # The lock in the backend should have a non-empty identifier
        lock_key = "lock:idempotency:key1"
        assert lock_key in backend._locks
        assert backend._locks[lock_key] is not None
        assert len(backend._locks[lock_key]) > 0  # UUID string
    
    @pytest.mark.asyncio
    async def test_lock_release_uses_correct_id(self, manager, backend):
        """Release should use the stored identifier from acquire."""
        await manager.acquire_lock("key2")
        lock_key = "lock:idempotency:key2"
        
        # Verify lock exists
        assert lock_key in backend._locks
        
        # Release
        await manager.release_lock("key2")
        
        # Lock should be removed
        assert lock_key not in backend._locks
    
    @pytest.mark.asyncio
    async def test_lock_release_without_acquire_warns(self, manager, caplog):
        """Releasing a lock that was never acquired should warn, not crash."""
        import logging
        with caplog.at_level(logging.WARNING, logger="eden.idempotency"):
            await manager.release_lock("never-acquired")
        
        assert "No lock identifier found" in caplog.text
    
    @pytest.mark.asyncio
    async def test_concurrent_lock_fails(self, manager):
        """Second lock attempt for same key should fail."""
        assert await manager.acquire_lock("conflict") is True
        assert await manager.acquire_lock("conflict") is False
    
    @pytest.mark.asyncio
    async def test_lock_after_release_succeeds(self, manager):
        """After releasing, re-acquisition should succeed."""
        assert await manager.acquire_lock("reuse") is True
        await manager.release_lock("reuse")
        assert await manager.acquire_lock("reuse") is True


class TestIdempotencyTTL:
    """Test that TTL is properly applied."""
    
    @pytest.mark.asyncio
    async def test_default_ttl_applied(self, manager, backend):
        """save_result should use default_ttl when not specified."""
        await manager.save_result("ttl-key", {"status": "ok"})
        
        # Check TTL was passed to backend
        assert backend._store.get("_ttl:idempotency:ttl-key") == 3600
    
    @pytest.mark.asyncio
    async def test_custom_ttl_applied(self, manager, backend):
        """save_result should use custom ttl_seconds when specified."""
        await manager.save_result("custom-ttl", {"status": "ok"}, ttl_seconds=7200)
        
        assert backend._store.get("_ttl:idempotency:custom-ttl") == 7200
    
    @pytest.mark.asyncio
    async def test_save_and_get_dict(self, manager):
        """Saving and retrieving a dict result should work."""
        data = {"amount": 100, "currency": "USD"}
        await manager.save_result("dict-key", data)
        
        result = await manager.get_result("dict-key")
        assert result == data
    
    @pytest.mark.asyncio
    async def test_save_and_get_scalar(self, manager):
        """Saving and retrieving a scalar value should work."""
        await manager.save_result("scalar-key", 42)
        
        result = await manager.get_result("scalar-key")
        assert result == {"_value": 42}


class TestIdempotencyUtilities:
    """Test delete_key and has_result."""
    
    @pytest.mark.asyncio
    async def test_delete_key(self, manager):
        """delete_key should remove the stored result."""
        await manager.save_result("del-key", {"ok": True})
        assert await manager.has_result("del-key") is True
        
        await manager.delete_key("del-key")
        assert await manager.has_result("del-key") is False
    
    @pytest.mark.asyncio
    async def test_has_result_false_for_missing(self, manager):
        """has_result should return False for non-existent keys."""
        assert await manager.has_result("missing") is False
    
    @pytest.mark.asyncio
    async def test_get_result_returns_none_for_missing(self, manager):
        """get_result should return None for non-existent keys."""
        assert await manager.get_result("missing") is None


class TestWithIdempotency:
    """Test the with_idempotency helper function."""
    
    @pytest.mark.asyncio
    async def test_executes_function_on_first_call(self, manager):
        """First call should execute the function and cache result."""
        call_count = 0
        
        async def process():
            nonlocal call_count
            call_count += 1
            return {"processed": True}
        
        result = await with_idempotency(manager, "first-call", process)
        
        assert result == {"processed": True}
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_returns_cached_on_second_call(self, manager):
        """Second call with same key should return cached result, not re-execute."""
        call_count = 0
        
        async def process():
            nonlocal call_count
            call_count += 1
            return {"processed": True}
        
        result1 = await with_idempotency(manager, "cached-call", process)
        result2 = await with_idempotency(manager, "cached-call", process)
        
        assert result1 == result2
        assert call_count == 1  # Only executed once
    
    @pytest.mark.asyncio
    async def test_no_manager_executes_directly(self):
        """When manager is None, function should execute directly."""
        async def process():
            return {"direct": True}
        
        result = await with_idempotency(None, "key", process)
        assert result == {"direct": True}
    
    @pytest.mark.asyncio
    async def test_no_key_executes_directly(self, manager):
        """When key is None, function should execute directly."""
        async def process():
            return {"no-key": True}
        
        result = await with_idempotency(manager, None, process)
        assert result == {"no-key": True}
    
    @pytest.mark.asyncio
    async def test_lock_released_on_exception(self, manager, backend):
        """Lock should be released even if the function raises."""
        async def failing_func():
            raise ValueError("Boom!")
        
        with pytest.raises(ValueError, match="Boom!"):
            await with_idempotency(manager, "error-key", failing_func)
        
        # Lock should have been released
        assert "lock:idempotency:error-key" not in backend._locks
    
    @pytest.mark.asyncio
    async def test_custom_ttl_forwarded(self, manager, backend):
        """ttl_seconds parameter should be forwarded to save_result."""
        async def process():
            return {"ttl": True}
        
        await with_idempotency(
            manager, "ttl-forward", process, ttl_seconds=600
        )
        
        assert backend._store.get("_ttl:idempotency:ttl-forward") == 600
