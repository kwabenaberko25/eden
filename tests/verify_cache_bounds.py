
import asyncio
import time
from eden.cache import InMemoryCache

async def test_cache_bounds():
    cache = InMemoryCache(max_size=5)
    
    # Fill cache
    for i in range(10):
        await cache.set(f"key_{i}", f"val_{i}")
    
    # Should only have 5 items
    data_size = len(cache._data)
    print(f"Final cache size: {data_size}")
    
    # Should have keys 5, 6, 7, 8, 9 (the last 5)
    remaining_keys = list(cache._data.keys())
    print(f"Remaining keys: {remaining_keys}")
    
    assert data_size == 5
    assert "key_9" in remaining_keys
    assert "key_0" not in remaining_keys
    
    print("Memory bounds test passed!")

if __name__ == "__main__":
    asyncio.run(test_cache_bounds())
