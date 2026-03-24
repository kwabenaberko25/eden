"""
Tests for Rate Limiting Middleware (Issue #21).

Verifies:
1. parse_rate_limit correctly parses various limit formats
2. MemoryRateLimitStore correctly counts and expires
3. generate_rate_limit_key produces deterministic keys
4. RateLimitMiddleware passes requests within limit
5. RateLimitMiddleware returns 429 when limit exceeded
6. Exempt paths bypass rate limiting
7. rate_limit decorator stores metadata on function
"""

import time
import pytest
from unittest.mock import AsyncMock, MagicMock
from eden.middleware.rate_limit import (
    parse_rate_limit,
    generate_rate_limit_key,
    MemoryRateLimitStore,
    RateLimitMiddleware,
    rate_limit,
)


class TestParseRateLimit:
    """Test rate limit string parsing."""
    
    def test_per_minute(self):
        count, ttl = parse_rate_limit("100/minute")
        assert count == 100
        assert ttl == 60
    
    def test_per_second(self):
        count, ttl = parse_rate_limit("10/second")
        assert count == 10
        assert ttl == 1
    
    def test_per_hour(self):
        count, ttl = parse_rate_limit("1000/hour")
        assert count == 1000
        assert ttl == 3600
    
    def test_per_day(self):
        count, ttl = parse_rate_limit("5/day")
        assert count == 5
        assert ttl == 86400
    
    def test_invalid_format_raises(self):
        with pytest.raises(ValueError):
            parse_rate_limit("invalid")
    
    def test_plural_forms(self):
        count, ttl = parse_rate_limit("50/minutes")
        assert count == 50
        assert ttl == 60


class TestMemoryRateLimitStore:
    """Test in-memory rate limit storage."""
    
    @pytest.mark.asyncio
    async def test_increment_and_get(self):
        store = MemoryRateLimitStore()
        count = await store.increment("test_key", ttl=60)
        assert count == 1
        
        count = await store.increment("test_key", ttl=60)
        assert count == 2
        
        current = await store.get_count("test_key")
        assert current == 2
    
    @pytest.mark.asyncio
    async def test_nonexistent_key_returns_zero(self):
        store = MemoryRateLimitStore()
        count = await store.get_count("nonexistent")
        assert count == 0
    
    @pytest.mark.asyncio
    async def test_reset_clears_count(self):
        store = MemoryRateLimitStore()
        await store.increment("test_key", ttl=60)
        await store.increment("test_key", ttl=60)
        
        await store.reset("test_key")
        count = await store.get_count("test_key")
        assert count == 0
    
    @pytest.mark.asyncio
    async def test_expired_key_returns_zero(self):
        store = MemoryRateLimitStore()
        # Set with very short TTL
        store._store["test_key"] = (5, time.time() - 1)  # Already expired
        
        count = await store.get_count("test_key")
        assert count == 0


class TestGenerateRateLimitKey:
    """Test rate limit key generation."""
    
    def test_deterministic(self):
        key1 = generate_rate_limit_key("192.168.1.1")
        key2 = generate_rate_limit_key("192.168.1.1")
        assert key1 == key2
    
    def test_different_ips_different_keys(self):
        key1 = generate_rate_limit_key("192.168.1.1")
        key2 = generate_rate_limit_key("10.0.0.1")
        assert key1 != key2
    
    def test_with_user_id(self):
        key1 = generate_rate_limit_key("192.168.1.1", user_id="user1")
        key2 = generate_rate_limit_key("192.168.1.1")
        assert key1 != key2
    
    def test_with_endpoint(self):
        key1 = generate_rate_limit_key("192.168.1.1", endpoint="/api/v1")
        key2 = generate_rate_limit_key("192.168.1.1", endpoint="/api/v2")
        assert key1 != key2


class TestRateLimitMiddleware:
    """Test the ASGI middleware."""
    
    @pytest.mark.asyncio
    async def test_passes_non_http_requests(self):
        """Non-HTTP scopes should pass through."""
        app = AsyncMock()
        middleware = RateLimitMiddleware(app, default_limit="10/minute")
        
        scope = {"type": "websocket"}
        receive = AsyncMock()
        send = AsyncMock()
        
        await middleware(scope, receive, send)
        app.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_exempt_paths_pass_through(self):
        """Exempt paths should bypass rate limiting."""
        app = AsyncMock()
        middleware = RateLimitMiddleware(
            app, 
            default_limit="10/minute",
            exempt_paths=["/health"]
        )
        
        scope = {"type": "http", "path": "/health", "client": ("127.0.0.1", 8000)}
        receive = AsyncMock()
        send = AsyncMock()
        
        await middleware(scope, receive, send)
        app.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_rate_limit_returns_429(self):
        """Should return 429 when limit is exceeded."""
        app = AsyncMock()
        middleware = RateLimitMiddleware(app, default_limit="2/minute")
        
        scope = {"type": "http", "path": "/api/test", "client": ("127.0.0.1", 8000)}
        receive = AsyncMock()
        
        # Make 3 requests (limit is 2)
        for i in range(3):
            sent_messages = []
            async def send(msg, msgs=sent_messages):
                msgs.append(msg)
            
            await middleware(scope, receive, send)
            
            if i < 2:
                # First 2 should pass
                app.assert_called()
            else:
                # Third should be 429
                assert any(
                    m.get("status") == 429 
                    for m in sent_messages 
                    if m.get("type") == "http.response.start"
                )


class TestRateLimitDecorator:
    """Test the @rate_limit decorator."""
    
    def test_stores_limit_metadata(self):
        @rate_limit("50/minute")
        async def my_endpoint(request):
            pass
        
        assert my_endpoint._rate_limit == "50/minute"
    
    def test_stores_key_function(self):
        key_fn = lambda req: req.user.id
        
        @rate_limit("50/minute", key=key_fn)
        async def my_endpoint(request):
            pass
        
        assert my_endpoint._rate_limit_key is key_fn
    
    def test_no_key_defaults_to_none(self):
        @rate_limit("50/minute")
        async def my_endpoint(request):
            pass
        
        assert my_endpoint._rate_limit_key is None
