import pytest
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.testclient import TestClient
from starlette.applications import Starlette

from eden.tenancy.middleware import TenantMiddleware
from eden.tenancy.exceptions import SecurityIsolationError


def test_tenant_middleware_enforcement_raises_security_isolation_error():
    async def app(scope, receive, send):
        response = JSONResponse({"message": "OK"})
        await response(scope, receive, send)

    # Wrap with our middleware, enforcing tenant
    middleware = TenantMiddleware(app, strategy="header", enforce=True)

    client = TestClient(middleware)
    with pytest.raises(SecurityIsolationError) as exc_info:
        # Request with no explicit tenant resolution mechanism
        client.get("/")

    assert "Tenant enforcement: request to / rejected \u2014 no tenant resolved" in str(exc_info.value)
