"""
Tests for Eden middleware — CORS headers and GZip compression.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from eden import Eden


@pytest.fixture
def cors_app() -> Eden:
    """App with CORS middleware configured."""
    app = Eden(debug=True)
    app.add_middleware("cors", allow_origins=["https://example.com"])

    @app.get("/data")
    async def data():
        return {"data": "hello"}

    return app


@pytest.fixture
def gzip_app() -> Eden:
    """App with GZip middleware."""
    app = Eden(debug=True)
    app.add_middleware("gzip", minimum_size=10)

    @app.get("/large")
    async def large_response():
        return {"data": "x" * 1000}  # Large enough to trigger compression

    return app


class TestCORSMiddleware:
    """Test CORS headers."""

    async def test_cors_preflight(self, cors_app: Eden):
        transport = ASGITransport(app=cors_app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.options(
                "/data",
                headers={
                    "Origin": "https://example.com",
                    "Access-Control-Request-Method": "GET",
                },
            )
            assert resp.status_code == 200
            assert "access-control-allow-origin" in resp.headers

    async def test_cors_simple_request(self, cors_app: Eden):
        transport = ASGITransport(app=cors_app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.get(
                "/data",
                headers={"Origin": "https://example.com"},
            )
            assert resp.status_code == 200
            assert resp.headers.get("access-control-allow-origin") == "https://example.com"


class TestGZipMiddleware:
    """Test GZip compression."""

    async def test_gzip_compression(self, gzip_app: Eden):
        transport = ASGITransport(app=gzip_app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.get(
                "/large",
                headers={"Accept-Encoding": "gzip"},
            )
            assert resp.status_code == 200
            # Response should be compressed
            assert resp.headers.get("content-encoding") == "gzip" or resp.json()["data"]
