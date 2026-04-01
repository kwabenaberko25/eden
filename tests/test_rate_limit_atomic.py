import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from eden.middleware.rate_limit import RedisRateLimitStore

@pytest.mark.asyncio
async def test_rate_limit_increment_is_atomic():
    store = RedisRateLimitStore("redis://localhost")
    store.redis = AsyncMock()
    
    # Mock redis.eval
    store.redis.eval.return_value = b'1'
    
    count = await store.increment("test_key", 60)
    
    assert count == 1
    # Check that eval was used
    store.redis.eval.assert_called_once_with(store.INCREMENT_SCRIPT, 1, "ratelimit:test_key", 60)
