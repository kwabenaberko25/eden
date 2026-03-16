
import pytest
from httpx import ASGITransport, AsyncClient
from eden import Eden, Router, View
from eden.requests import Request
from eden.responses import json

class HelloView(View):
    """A simple class-based view."""
    async def get(self, request: Request):
        return {"message": "Hello from CBV!"}
    
    async def post(self, request: Request):
        data = await request.json()
        return {"received": data}

@pytest.fixture
def app():
    app = Eden(debug=True)
    router = Router()
    
    # Register view
    router.add_view("/hello", HelloView)
    
    # Sub-router with view
    api = Router(prefix="/api")
    api.add_view("/hello", HelloView)
    router.include_router(api)
    
    app.include_router(router)
    return app

@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c

@pytest.mark.asyncio
async def test_cbv_get(client):
    resp = await client.get("/hello")
    # This will fail until View and add_view are implemented
    assert resp.status_code == 200
    assert resp.json() == {"message": "Hello from CBV!"}

@pytest.mark.asyncio
async def test_cbv_post(client):
    resp = await client.post("/hello", json={"name": "Eden"})
    assert resp.status_code == 200
    assert resp.json() == {"received": {"name": "Eden"}}

@pytest.mark.asyncio
async def test_cbv_subrouter(client):
    resp = await client.get("/api/hello")
    assert resp.status_code == 200
    assert resp.json() == {"message": "Hello from CBV!"}
