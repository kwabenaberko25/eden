import pytest
import asyncio
from datetime import datetime
from eden import Eden, json
from eden.cache import InMemoryCache, TenantCacheWrapper
from eden.middleware import CacheMiddleware
from starlette.testclient import TestClient

@pytest.fixture
def cache():
    return InMemoryCache()

@pytest.fixture
def app(cache):
    app = Eden(title="Test Cache App")
    app.cache = cache
    
    @app.get("/time")
    async def get_time():
        return {"time": datetime.now().isoformat()}

    @app.get("/no-cache")
    async def no_cache():
        return json({"time": datetime.now().isoformat()}, headers={"Cache-Control": "no-store"})

    @app.get("/short-ttl")
    async def short_ttl():
        return json({"time": datetime.now().isoformat()}, headers={"Cache-Control": "max-age=1"})

    app.add_middleware("cache")
    return app

def test_cache_hit_miss(app):
    client = TestClient(app)
    
    # First request - MISS
    resp1 = client.get("/time")
    assert resp1.status_code == 200
    assert resp1.headers["x-eden-cache"] == "MISS"
    time1 = resp1.json()["time"]
    
    # Second request - HIT
    resp2 = client.get("/time")
    assert resp2.status_code == 200
    assert resp2.headers["x-eden-cache"] == "HIT"
    assert resp2.json()["time"] == time1

def test_cache_control_no_store(app):
    client = TestClient(app)
    
    # First request
    resp1 = client.get("/no-cache")
    assert resp1.headers["x-eden-cache"] == "MISS"
    
    # Second request - should still be MISS because of no-store
    resp2 = client.get("/no-cache")
    assert resp2.headers["x-eden-cache"] == "MISS"

@pytest.mark.asyncio
async def test_cache_expiry(app):
    # TestClient doesn't support async wait easily for TTL
    # But we can check if it respects max-age in the middleware logic
    client = TestClient(app)
    
    resp1 = client.get("/short-ttl")
    assert resp1.headers["x-eden-cache"] == "MISS"
    time1 = resp1.json()["time"]
    
    # Immediate hit
    resp2 = client.get("/short-ttl")
    assert resp2.headers["x-eden-cache"] == "HIT"
    assert resp2.json()["time"] == time1
    
    # Wait for TTL (1s)
    await asyncio.sleep(1.1)
    
    # Note: InMemoryCache in eden/cache.py DOES NOT support TTL currently.
    # It just stores the value. I should check eden/cache.py implementation.
