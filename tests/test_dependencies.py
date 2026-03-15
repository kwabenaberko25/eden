"""
Tests for Eden dependency injection — simple deps, nested deps,
async generators (cleanup), and per-request caching.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from eden import Depends, Eden


# Track call counts for caching tests
_call_counts: dict[str, int] = {}


def reset_counts():
    _call_counts.clear()


@pytest.fixture(autouse=True)
def _reset():
    reset_counts()


@pytest.fixture
def app() -> Eden:
    app = Eden(debug=True)

    # Simple dependency
    async def get_db_connection():
        _call_counts["db"] = _call_counts.get("db", 0) + 1
        return {"connection": "active"}

    # Nested dependency
    async def get_user_repo(db=Depends(get_db_connection)):
        return {"repo": "users", "db": db}

    # Generator dependency (with cleanup)
    cleanup_log: list[str] = []

    async def get_session():
        cleanup_log.append("opened")
        yield {"session": "abc123"}
        cleanup_log.append("closed")

    @app.get("/simple")
    async def simple_dep(db=Depends(get_db_connection)):
        return {"db": db}

    @app.get("/nested")
    async def nested_dep(repo=Depends(get_user_repo)):
        return {"repo": repo}

    @app.get("/cached")
    async def cached_dep(
        db1=Depends(get_db_connection),
        db2=Depends(get_db_connection),
    ):
        return {"same": db1 is db2, "call_count": _call_counts.get("db", 0)}

    @app.get("/gen")
    async def generator_dep(session=Depends(get_session)):
        return {"session": session}

    @app.get("/cleanup-log")
    async def get_cleanup_log():
        return {"log": cleanup_log}

    return app


@pytest.fixture
async def client(app: Eden) -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


class TestDependencyInjection:
    """Test the Depends() system."""

    async def test_simple_dependency(self, client: AsyncClient):
        resp = await client.get("/simple")
        assert resp.status_code == 200
        data = resp.json()
        assert data["db"] == {"connection": "active"}

    async def test_nested_dependency(self, client: AsyncClient):
        resp = await client.get("/nested")
        assert resp.status_code == 200
        data = resp.json()
        assert data["repo"]["repo"] == "users"
        assert data["repo"]["db"]["connection"] == "active"

    async def test_cached_dependency(self, client: AsyncClient):
        resp = await client.get("/cached")
        assert resp.status_code == 200
        data = resp.json()
        # Should only be called once due to caching
        assert data["call_count"] == 1

    async def test_generator_dependency(self, client: AsyncClient):
        resp = await client.get("/gen")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session"]["session"] == "abc123"

    async def test_generator_cleanup(self, client: AsyncClient):
        # First call the gen endpoint to trigger open+close
        await client.get("/gen")
        # Then check the log
        resp = await client.get("/cleanup-log")
        data = resp.json()
        assert "opened" in data["log"]
        assert "closed" in data["log"]
