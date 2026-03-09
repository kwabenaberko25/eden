"""
Tests for Eden request handling — JSON body, query params, headers.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from eden import Eden, Request


@pytest.fixture
def app() -> Eden:
    app = Eden(debug=True)

    @app.get("/query")
    async def with_query(request: Request):
        name = request.get_query("name", "World")
        page = request.get_query("page", "1")
        return {"name": name, "page": page}

    @app.get("/query-list")
    async def with_query_list(request: Request):
        tags = request.get_query_list("tag")
        return {"tags": tags}

    @app.post("/json-body")
    async def with_json_body(request: Request):
        body = await request.json_body()
        return {"received": body}

    @app.get("/headers")
    async def with_headers(request: Request):
        auth = request.get_header("Authorization")
        custom = request.get_header("X-Custom-Header", "none")
        return {"auth": auth, "custom": custom}

    @app.get("/info")
    async def request_info(request: Request):
        return {
            "method": request.method,
            "path": request.url.path,
            "is_json": request.is_json,
        }

    return app


@pytest.fixture
async def client(app: Eden) -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


class TestRequests:
    """Test request parsing and access methods."""

    async def test_query_params(self, client: AsyncClient):
        resp = await client.get("/query?name=Eden&page=3")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Eden"
        assert data["page"] == "3"

    async def test_query_defaults(self, client: AsyncClient):
        resp = await client.get("/query")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "World"
        assert data["page"] == "1"

    async def test_query_list(self, client: AsyncClient):
        resp = await client.get("/query-list?tag=python&tag=async&tag=eden")
        assert resp.status_code == 200
        data = resp.json()
        assert data["tags"] == ["python", "async", "eden"]

    async def test_json_body(self, client: AsyncClient):
        payload = {"title": "Eden", "version": "0.1.0"}
        resp = await client.post("/json-body", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["received"] == payload

    async def test_custom_headers(self, client: AsyncClient):
        resp = await client.get(
            "/headers",
            headers={
                "Authorization": "Bearer abc123",
                "X-Custom-Header": "custom-value",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["auth"] == "Bearer abc123"
        assert data["custom"] == "custom-value"

    async def test_request_info(self, client: AsyncClient):
        resp = await client.get("/info")
        assert resp.status_code == 200
        data = resp.json()
        assert data["method"] == "GET"
        assert data["path"] == "/info"
