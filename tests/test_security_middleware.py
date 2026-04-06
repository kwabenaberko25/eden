"""
Tests for Eden Security, Rate Limiting, Logging Middleware, and Health Checks.
"""

import asyncio
import time

import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from eden.middleware import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
)


# ── Helpers ──────────────────────────────────────────────────────────────


def _make_app(middleware_cls, **kwargs):
    """Create a minimal Starlette app with the given middleware."""

    async def homepage(request):
        return PlainTextResponse("OK")

    app = Starlette(routes=[Route("/", homepage), Route("/exempt", homepage)])
    app.add_middleware(middleware_cls, **kwargs)
    return app


# ── Security Headers Tests ───────────────────────────────────────────────


class TestSecurityHeadersMiddleware:
    """Test the SecurityHeadersMiddleware."""

    def test_default_headers_present(self):
        app = _make_app(SecurityHeadersMiddleware)
        client = TestClient(app)
        resp = client.get("/")

        assert resp.status_code == 200
        assert resp.headers["x-content-type-options"] == "nosniff"
        assert resp.headers["x-frame-options"] == "DENY"
        assert resp.headers["x-xss-protection"] == "1; mode=block"
        assert resp.headers["referrer-policy"] == "strict-origin-when-cross-origin"
        assert "camera=()" in resp.headers["permissions-policy"]

    def test_hsts_header(self):
        app = _make_app(SecurityHeadersMiddleware, hsts=True, hsts_max_age=3600)
        client = TestClient(app)
        resp = client.get("/")

        hsts = resp.headers["strict-transport-security"]
        assert "max-age=3600" in hsts
        assert "includeSubDomains" in hsts

    def test_hsts_preload(self):
        app = _make_app(SecurityHeadersMiddleware, hsts=True, hsts_preload=True)
        client = TestClient(app)
        resp = client.get("/")

        hsts = resp.headers["strict-transport-security"]
        assert "preload" in hsts

    def test_hsts_disabled(self):
        app = _make_app(SecurityHeadersMiddleware, hsts=False)
        client = TestClient(app)
        resp = client.get("/")

        assert "strict-transport-security" not in resp.headers

    def test_custom_csp(self):
        app = _make_app(SecurityHeadersMiddleware, csp="default-src 'self'")
        client = TestClient(app)
        resp = client.get("/")

        assert resp.headers["content-security-policy"] == "default-src 'self'"

    def test_custom_frame_options(self):
        app = _make_app(SecurityHeadersMiddleware, frame_options="SAMEORIGIN")
        client = TestClient(app)
        resp = client.get("/")

        assert resp.headers["x-frame-options"] == "SAMEORIGIN"

    def test_custom_headers(self):
        app = _make_app(
            SecurityHeadersMiddleware,
            custom_headers={"X-Custom": "test-value"},
        )
        client = TestClient(app)
        resp = client.get("/")

        assert resp.headers["x-custom"] == "test-value"


# ── Rate Limit Tests ─────────────────────────────────────────────────────


class TestRateLimitMiddleware:
    """Test the RateLimitMiddleware."""

    def test_allows_under_limit(self):
        app = _make_app(RateLimitMiddleware, max_requests=10, window_seconds=60)
        client = TestClient(app)

        for _ in range(10):
            resp = client.get("/")
            assert resp.status_code == 200

    def test_blocks_over_limit(self):
        app = _make_app(RateLimitMiddleware, max_requests=5, window_seconds=60)
        client = TestClient(app)

        # Use up the limit
        for _ in range(5):
            resp = client.get("/")
            assert resp.status_code == 200

        # Next request should be rate limited
        resp = client.get("/")
        assert resp.status_code == 429
        data = resp.json()
        assert data["error"] is True
        assert "Too many requests" in data["detail"]
        assert "retry-after" in resp.headers

    def test_exempt_paths(self):
        app = _make_app(
            RateLimitMiddleware,
            max_requests=1,
            window_seconds=60,
            exempt_paths=["/exempt"],
        )
        client = TestClient(app)

        # First request exhausts the limit
        resp = client.get("/")
        assert resp.status_code == 200

        # Second request to non-exempt path is blocked
        resp = client.get("/")
        assert resp.status_code == 429

        # But exempt path still works
        resp = client.get("/exempt")
        assert resp.status_code == 200


# ── Health Check Tests ───────────────────────────────────────────────────


class TestHealthChecks:
    """Test the Eden health check system."""

    def test_health_endpoint(self):
        from eden import Eden

        app = Eden(title="TestApp", version="1.0.0")
        app.enable_health_checks()

        # Build starlette app for testing
        from starlette.testclient import TestClient as StarletteClient

        client = StarletteClient(app)
        resp = client.get("/health")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["app"] == "TestApp"
        assert data["version"] == "1.0.0"

    def test_ready_endpoint_no_checks(self):
        from eden import Eden

        app = Eden(title="TestApp")
        app.enable_health_checks()

        client = TestClient(app)
        resp = client.get("/ready")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert data["checks"] == {}

    def test_ready_endpoint_passing_check(self):
        from eden import Eden

        app = Eden(title="TestApp")
        app.enable_health_checks()
        app.add_readiness_check("always_ok", lambda: True)

        client = TestClient(app)
        resp = client.get("/ready")

        data = resp.json()
        assert data["status"] == "ready"
        assert data["checks"]["always_ok"]["status"] == "ok"

    def test_ready_endpoint_failing_check(self):
        from eden import Eden

        app = Eden(title="TestApp")
        app.enable_health_checks()
        app.add_readiness_check("always_fail", lambda: False)

        client = TestClient(app)
        resp = client.get("/ready")

        data = resp.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["always_fail"]["status"] == "fail"

    def test_ready_endpoint_exception_check(self):
        from eden import Eden

        def exploding_check():
            raise ConnectionError("DB down")

        app = Eden(title="TestApp")
        app.enable_health_checks()
        app.add_readiness_check("db", exploding_check)

        client = TestClient(app)
        resp = client.get("/ready")

        data = resp.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["db"]["status"] == "fail"
        assert "DB down" in data["checks"]["db"]["error"]


# ── Request Logging Tests ────────────────────────────────────────────────


class TestRequestLoggingMiddleware:
    """Test the RequestLoggingMiddleware."""

    def test_adds_request_id_header(self):
        from eden.logging import RequestLoggingMiddleware

        app = _make_app(RequestLoggingMiddleware)
        client = TestClient(app)
        resp = client.get("/")

        assert resp.status_code == 200
        assert "x-request-id" in resp.headers
        assert len(resp.headers["x-request-id"]) > 0

    def test_excludes_health_path(self):
        from eden.logging import RequestLoggingMiddleware

        async def health(request):
            return PlainTextResponse("ok")

        app = Starlette(
            routes=[Route("/", lambda r: PlainTextResponse("OK")), Route("/health", health)]
        )
        app.add_middleware(RequestLoggingMiddleware)
        client = TestClient(app)

        # Health path should not get a request ID (excluded from logging)
        resp = client.get("/health")
        assert resp.status_code == 200
        assert "x-request-id" not in resp.headers

    def test_preserves_incoming_request_id(self):
        from eden.logging import RequestLoggingMiddleware

        app = _make_app(RequestLoggingMiddleware)
        client = TestClient(app)
        resp = client.get("/", headers={"X-Request-ID": "custom-id-123"})

        assert resp.headers["x-request-id"] == "custom-id-123"

    def test_generates_full_uuid_request_id(self):
        import uuid
        from eden.logging import RequestLoggingMiddleware

        app = _make_app(RequestLoggingMiddleware)
        client = TestClient(app)
        resp = client.get("/")

        assert resp.status_code == 200
        assert "x-request-id" in resp.headers
        # Generated IDs should be a full UUID string, not a truncated hex fragment.
        uuid.UUID(resp.headers["x-request-id"])

    def test_sets_request_id_in_context(self):
        from eden.context import get_request_id
        from eden.logging import RequestLoggingMiddleware

        async def handler(request):
            return PlainTextResponse(get_request_id())

        app = Starlette(routes=[Route("/", handler)])
        app.add_middleware(RequestLoggingMiddleware)
        client = TestClient(app)

        resp = client.get("/")
        assert resp.status_code == 200
        assert resp.text == resp.headers["x-request-id"]
