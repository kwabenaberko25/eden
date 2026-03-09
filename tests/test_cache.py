import pytest
import asyncio
from starlette.responses import PlainTextResponse
from eden.cache import cache_view, InMemoryCache
from unittest.mock import Mock

@pytest.mark.asyncio
async def test_cache_view_decorator():
    cache = InMemoryCache()
    call_count = 0
    
    @cache_view(ttl=60, cache=cache)
    async def my_view(request):
        nonlocal call_count
        call_count += 1
        return PlainTextResponse(f"Count: {call_count}")
        
    class MockRequest:
        url = type('URL', (), {'path': '/test-path'})()
        headers = {}
        state = type('State', (), {'user': None})()
        
    req = MockRequest()
    
    # First call - should execute view
    res1 = await my_view(req)
    assert res1.body == b"Count: 1"
    
    # Second call - should hit cache
    res2 = await my_view(req)
    assert res2.body == b"Count: 1"  # Still 1!
    
    assert call_count == 1
    
@pytest.mark.asyncio
async def test_cache_view_vary_on_user():
    cache = InMemoryCache()
    call_count = 0
    
    @cache_view(ttl=60, cache=cache, vary_on_user=True)
    async def my_view(request):
        nonlocal call_count
        call_count += 1
        return PlainTextResponse(f"Count: {call_count} User: {request.user.id}")
        
    class MockUser:
        def __init__(self, uid):
            self.id = uid
            self.is_authenticated = True
            
    class MockRequest:
        def __init__(self, uid):
            self.url = type('URL', (), {'path': '/dashboard'})()
            self.user = MockUser(uid)
            self.headers = {}
            self.state = type('State', (), {'user': self.user})()
            
    req1 = MockRequest(1)
    req2 = MockRequest(2)
    
    # User 1 first call
    res_u1_1 = await my_view(req1)
    assert res_u1_1.body == b"Count: 1 User: 1"
    
    # User 2 first call (different user, should miss cache)
    res_u2_1 = await my_view(req2)
    assert res_u2_1.body == b"Count: 2 User: 2"
    
    # User 1 second call (should hit cache)
    res_u1_2 = await my_view(req1)
    assert res_u1_2.body == b"Count: 1 User: 1"
    
    assert call_count == 2
