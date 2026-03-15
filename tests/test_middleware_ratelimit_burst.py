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
    
    # 1. Mock RedisRateLimitStore within the middleware
    with patch("eden.middleware.rate_limit.RedisRateLimitStore") as mock_store_cls:
        mock_store = mock_store_cls.return_value
        
        # Simulate counter
        counters = {}
        async def mock_increment(key, ttl):
            counters[key] = counters.get(key, 0) + 1
            return counters[key]
        
        mock_store.increment = AsyncMock(side_effect=mock_increment)

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
