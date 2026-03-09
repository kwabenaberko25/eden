import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import MagicMock, patch, AsyncMock
from eden import Eden

@pytest.fixture
def ratelimit_app() -> Eden:
    app = Eden(debug=True)
    # 2 requests per 60 seconds for testing
    app.add_middleware("redis_ratelimit", max_requests=2, window_seconds=60, redis_url="redis://localhost")
    
    @app.get("/")
    async def index():
        return {"ok": True}
        
    return app

@pytest.mark.asyncio
async def test_redis_ratelimit_burst(ratelimit_app: Eden):
    """Verify that RedisRateLimitMiddleware denies requests after the limit is reached."""
    
    # 1. Mock RedisCache within the middleware
    # Note: Middleware imports RedisCache inside _get_cache
    with patch("eden.cache.redis.RedisCache") as mock_cache_cls:
        mock_cache = mock_cache_cls.return_value
        mock_cache.connect = AsyncMock()
        
        # Simulate counter in Redis
        counters = {}
        async def mock_incr(key):
            counters[key] = counters.get(key, 0) + 1
            return counters[key]
        
        mock_cache.incr = AsyncMock(side_effect=mock_incr)
        mock_cache._client = MagicMock()
        mock_cache._client.expire = AsyncMock()
        mock_cache._client.ttl = AsyncMock(return_value=60)
        mock_cache._key = lambda k: f"ratelimit:{k}"

        transport = ASGITransport(app=ratelimit_app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # Request 1: OK
            resp1 = await client.get("/")
            assert resp1.status_code == 200
            
            # Request 2: OK
            resp2 = await client.get("/")
            assert resp2.status_code == 200
            
            # Request 3: 429 TOO MANY REQUESTS
            resp3 = await client.get("/")
            assert resp3.status_code == 429
            assert resp3.json()["detail"] == "Too many requests. Please slow down."
            assert "Retry-After" in resp3.headers
