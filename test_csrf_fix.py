"""
Tests for CSRF token generation with and without session middleware.
"""

import pytest
from starlette.requests import Request
from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from eden.security.csrf import get_csrf_token, generate_csrf_token, CSRFMiddleware


# ──────────────────────────────────────────────────────────────────────────
# Test 1: CSRF token generation
# ──────────────────────────────────────────────────────────────────────────

def test_generate_csrf_token():
    """Test that CSRF tokens are generated correctly."""
    token1 = generate_csrf_token()
    token2 = generate_csrf_token()
    
    assert token1, "Token should not be empty"
    assert token2, "Token should not be empty"
    assert token1 != token2, "Tokens should be unique"
    assert len(token1) > 20, "Token should be reasonably long"
    print("[PASS] CSRF token generation works")


# ──────────────────────────────────────────────────────────────────────────
# Test 2: get_csrf_token with session
# ──────────────────────────────────────────────────────────────────────────

def test_get_csrf_token_with_session():
    """Test getting CSRF token when session middleware is configured."""
    app = Starlette()
    app.add_middleware(SessionMiddleware, secret_key="test-secret")
    
    @app.route("/get-token")
    async def get_token(request: Request):
        token = get_csrf_token(request)
        return JSONResponse({"token": token})
    
    client = TestClient(app)
    response = client.get("/get-token")
    
    assert response.status_code == 200, f"Status: {response.status_code}"
    data = response.json()
    assert "token" in data, "Response should have token"
    assert len(data["token"]) > 20, "Token should be non-empty"
    
    # Token should be consistent in subsequent requests
    response2 = client.get("/get-token")
    data2 = response2.json()
    assert data["token"] == data2["token"], "Token should be consistent across requests"
    
    print("[PASS] CSRF token with session works")


# ──────────────────────────────────────────────────────────────────────────
# Test 3: get_csrf_token without session (fallback)
# ──────────────────────────────────────────────────────────────────────────

def test_get_csrf_token_without_session():
    """Test that get_csrf_token handles missing session gracefully."""
    app = Starlette()
    # NOTE: No SessionMiddleware added - session should be unavailable
    
    @app.route("/get-token")
    async def get_token(request: Request):
        token = get_csrf_token(request)
        # Check if session is available by checking scope, not via hasattr
        has_session = "session" in request.scope
        return JSONResponse({"token": token, "has_session": has_session})
    
    client = TestClient(app)
    response = client.get("/get-token")
    
    assert response.status_code == 200, f"Should not crash, status: {response.status_code}"
    data = response.json()
    assert "token" in data, "Should still return a token"
    assert len(data["token"]) > 20, "Fallback token should be non-empty"
    assert data["has_session"] is False, "Session should not be available"
    
    print("[PASS] CSRF token fallback (no session) works")


# ──────────────────────────────────────────────────────────────────────────
# Test 4: CSRF Middleware protects against attacks
# ──────────────────────────────────────────────────────────────────────────

def test_csrf_middleware_validation():
    """Test that CSRF middleware validates tokens on POST requests."""
    from starlette.middleware import Middleware
    
    # Create app with proper middleware stack
    # Note: In Starlette, middleware added later execute first (outermost)
    # So we add CSRF first, then Session, so Session is outermost
    app = Starlette(
        middleware=[
            Middleware(SessionMiddleware, secret_key="test-secret"),
            Middleware(CSRFMiddleware),
        ]
    )
    
    @app.route("/token", methods=["GET"])
    async def get_token_endpoint(request: Request):
        from eden.security.csrf import CSRF_SECRET_KEY
        token = get_csrf_token(request)
        return JSONResponse({"token": token})
    
    @app.route("/submit", methods=["POST"])
    async def submit_form(request: Request):
        return JSONResponse({"success": True})
    
    client = TestClient(app)
    
    # Get CSRF token first
    response = client.get("/token")
    assert response.status_code == 200
    token = response.json()["token"]
    
    # POST with correct token should succeed
    response = client.post("/submit", data={"csrf_token": token})
    assert response.status_code == 200, f"Correct token should be accepted, got {response.status_code}"
    
    # POST with missing token should fail
    response = client.post("/submit")
    assert response.status_code == 403, f"Missing token should be rejected, got {response.status_code}"
    
    # POST with wrong token should fail
    response = client.post("/submit", data={"csrf_token": "wrong_token"})
    assert response.status_code == 403, f"Wrong token should be rejected, got {response.status_code}"
    
    print("[PASS] CSRF middleware validation works")


# ──────────────────────────────────────────────────────────────────────────
# Run all tests
# ──────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_generate_csrf_token()
    test_get_csrf_token_with_session()
    test_get_csrf_token_without_session()
    test_csrf_middleware_validation()
    print("\n✅ All CSRF tests passed!")
