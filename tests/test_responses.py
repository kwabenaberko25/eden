"""
Tests for Eden responses — JSON serialization, Pydantic models,
status codes, cookies, and shortcut functions.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel

from eden import Eden
from eden.responses import JsonResponse, json, html, redirect


class UserModel(BaseModel):
    id: int
    name: str
    email: str


@pytest.fixture
def app() -> Eden:
    app = Eden(debug=True)

    @app.get("/dict")
    async def return_dict():
        return {"key": "value", "number": 42}

    @app.get("/list")
    async def return_list():
        return [1, 2, 3]

    @app.get("/pydantic")
    async def return_pydantic():
        user = UserModel(id=1, name="Eden", email="eden@example.com")
        return JsonResponse(content=user)

    @app.get("/nested-pydantic")
    async def return_nested():
        users = [
            UserModel(id=1, name="Alice", email="alice@eden.dev"),
            UserModel(id=2, name="Bob", email="bob@eden.dev"),
        ]
        return JsonResponse(content={"users": users, "count": 2})

    @app.get("/status-created")
    async def return_created():
        return JsonResponse(content={"created": True}, status_code=201)

    @app.get("/html")
    async def return_html():
        return html("<h1>Hello Eden</h1>")

    @app.get("/shortcut-json")
    async def return_json_shortcut():
        return json({"shortcut": True}, status_code=201)

    @app.get("/redirect")
    async def return_redirect():
        return redirect("/destination")

    return app


@pytest.fixture
async def client(app: Eden) -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


class TestResponses:
    """Test response serialization and status codes."""

    async def test_dict_response(self, client: AsyncClient):
        resp = await client.get("/dict")
        assert resp.status_code == 200
        assert resp.json() == {"key": "value", "number": 42}

    async def test_list_response(self, client: AsyncClient):
        resp = await client.get("/list")
        assert resp.status_code == 200
        assert resp.json() == [1, 2, 3]

    async def test_pydantic_serialization(self, client: AsyncClient):
        resp = await client.get("/pydantic")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 1
        assert data["name"] == "Eden"
        assert data["email"] == "eden@example.com"

    async def test_nested_pydantic(self, client: AsyncClient):
        resp = await client.get("/nested-pydantic")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2
        assert len(data["users"]) == 2
        assert data["users"][0]["name"] == "Alice"

    async def test_custom_status_code(self, client: AsyncClient):
        resp = await client.get("/status-created")
        assert resp.status_code == 201

    async def test_html_response(self, client: AsyncClient):
        resp = await client.get("/html")
        assert resp.status_code == 200
        assert "<h1>Hello Eden</h1>" in resp.text

    async def test_json_shortcut(self, client: AsyncClient):
        resp = await client.get("/shortcut-json")
        assert resp.status_code == 201
        assert resp.json() == {"shortcut": True}

    async def test_redirect_response(self, client: AsyncClient):
        resp = await client.get("/redirect", follow_redirects=False)
        assert resp.status_code == 307
        assert resp.headers["location"] == "/destination"
