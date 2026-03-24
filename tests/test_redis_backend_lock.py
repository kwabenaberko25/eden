import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from eden.core.backends.redis import RedisBackend

@pytest.mark.asyncio
async def test_redis_lock_release_bug():
    """
    Verifies that release_lock uses the correct Lua script logic and handles interaction
    with the mock Redis client correctly.
    """
    mock_redis = AsyncMock()
    # Simulate EVAL returning 1 for success
    mock_redis.eval.return_value = 1
    
    with patch("redis.asyncio.from_url", return_value=mock_redis):
        backend = RedisBackend(url="redis://localhost:6379/0")
        await backend.connect()
        
        # Test acquire
        mock_redis.set.return_value = True
        acquired = await backend.acquire_lock("test_lock", identifier="my_id")
        assert acquired is True
        
        # Test release
        released = await backend.release_lock("test_lock", "my_id")
        assert released is True
        
        # Verify EVAL arguments
        # args: (script, num_keys, *keys, *args)
        call_args = mock_redis.eval.call_args
        script = call_args[0][0]
        num_keys = call_args[0][1]
        key = call_args[0][2]
        identifier = call_args[0][3]
        
        assert num_keys == 1
        assert "eden:lock:test_lock" in key
        assert identifier == "my_id"
        
        # Check script for common pitfalls (like leading indentation in multi-line string if not dedented)
        # Lua is sensitive to syntax. Multiple spaces are fine, but let's ensure it's clean.
        assert 'if redis.call("get", KEYS[1]) == ARGV[1] then' in script

def test_redis_backend_init():
    """Check init logic with host/port."""
    backend = RedisBackend(host="my-host", port=1234, db=5)
    assert backend.url == "redis://my-host:1234/5"
