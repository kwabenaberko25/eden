import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.testclient import TestClient
from eden.auth.middleware import AuthenticationMiddleware
from eden.auth.base import AuthBackend
from eden.requests import Request

# ── Mock Backend ──────────────────────────────────────────────────────────

class FailingBackend(AuthBackend):
    async def authenticate(self, request: Request):
        raise Exception("Database Connection Refused")

class SuccessBackend(AuthBackend):
    async def authenticate(self, request: Request):
        # Mock user object
        class MockUser:
            id = "user_123"
        return MockUser()

# ── Audit Tests ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_auth_middleware_failure_resilience():
    """
    AUDIT 3.1: Backend Failure Resilience.
    Verify that a single failing backend does not crash the entire request
    if other backends are present, OR that it is handled gracefully.
    
    Currently, AuthenticationMiddleware loops through backends.
    If a backend raises an exception, it might crash the middleware.
    """
    
    async def homepage(request):
        user = getattr(request.state, "user", None)
        return JSONResponse({"user": user.id if user else None})

    # Scenario 1: Failing backend followed by success backend
    # If the failing one crashes the loop, the request fails.
    app = Starlette()
    app.add_middleware(
        AuthenticationMiddleware, 
        backends=[FailingBackend(), SuccessBackend()]
    )
    app.add_route("/", homepage)
    
    client = TestClient(app)
    
    # This might raise 500 if middleware doesn't catch the backend exception
    response = client.get("/")
    
    # Audit finding: If this is 500, the middleware is NOT resilient.
    if response.status_code == 500:
        pytest.fail("AuthenticationMiddleware is NOT resilient to backend exceptions.")
    
    assert response.status_code == 200
    assert response.json()["user"] == "user_123"

@pytest.mark.asyncio
async def test_auth_middleware_all_failing():
    """
    Verify behavior when all backends fail.
    """
    async def homepage(request):
        return JSONResponse({"ok": True})

    app = Starlette()
    app.add_middleware(
        AuthenticationMiddleware, 
        backends=[FailingBackend()]
    )
    app.add_route("/", homepage)
    
    client = TestClient(app)
    response = client.get("/")
    
    # If this is 200, it confirms resilience
    assert response.status_code == 200
