"""
Tests for Eden routing — route registration, path params,
method filtering, sub-routers, and 404/405 handling.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from eden import Eden, NotFound, Router


@pytest.fixture
def app() -> Eden:
    app = Eden(debug=True)

    @app.get("/")
    async def index():
        return {"message": "hello"}

    @app.get("/greet/{name}")
    async def greet(name: str):
        return {"greeting": f"Hello, {name}!"}

    @app.get("/items/{item_id:int}")
    async def get_item(item_id: int):
        return {"item_id": item_id}

    @app.post("/items")
    async def create_item():
        return {"created": True}

    @app.put("/items/{item_id:int}")
    async def update_item(item_id: int):
        return {"updated": item_id}

    @app.delete("/items/{item_id:int}")
    async def delete_item(item_id: int):
        return {"deleted": item_id}

    # Sub-router
    api = Router(prefix="/api/v1")

    @api.get("/status")
    async def status():
        return {"status": "ok"}

    @api.get("/users/{user_id:int}")
    async def get_user(user_id: int):
        return {"user_id": user_id}

    app.include_router(api)

    return app


@pytest.fixture
async def client(app: Eden) -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


class TestRouteRegistration:
    """Test basic route registration and matching."""

    async def test_root_route(self, client: AsyncClient):
        resp = await client.get("/")
        assert resp.status_code == 200
        assert resp.json() == {"message": "hello"}

    async def test_path_param_string(self, client: AsyncClient):
        resp = await client.get("/greet/Eden")
        assert resp.status_code == 200
        assert resp.json() == {"greeting": "Hello, Eden!"}

    async def test_path_param_int(self, client: AsyncClient):
        resp = await client.get("/items/42")
        assert resp.status_code == 200
        assert resp.json() == {"item_id": 42}

    async def test_post_route(self, client: AsyncClient):
        resp = await client.post("/items")
        assert resp.status_code == 200
        assert resp.json() == {"created": True}

    async def test_put_route(self, client: AsyncClient):
        resp = await client.put("/items/5")
        assert resp.status_code == 200
        assert resp.json() == {"updated": 5}

    async def test_delete_route(self, client: AsyncClient):
        resp = await client.delete("/items/5")
        assert resp.status_code == 200
        assert resp.json() == {"deleted": 5}


class TestSubRouter:
    """Test sub-router prefix merging."""

    async def test_sub_router_route(self, client: AsyncClient):
        resp = await client.get("/api/v1/status")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    async def test_sub_router_path_param(self, client: AsyncClient):
        resp = await client.get("/api/v1/users/7")
        assert resp.status_code == 200
        assert resp.json() == {"user_id": 7}


class TestErrorHandling:
    """Test 404 and 405 responses."""

    async def test_404_not_found(self, client: AsyncClient):
        resp = await client.get("/nonexistent")
        assert resp.status_code == 404
        data = resp.json()
        assert data["error"] is True

    async def test_405_method_not_allowed(self, client: AsyncClient):
        resp = await client.delete("/")  # Only GET is registered
        assert resp.status_code == 405
        data = resp.json()
        assert data["error"] is True
