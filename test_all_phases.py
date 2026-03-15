"""
COMPREHENSIVE TEST SUITE FOR EDEN CRITICAL GAPS FIXES
Tests for: ORM Methods, CSRF Fix, OpenAPI Documentation
"""

import pytest
import json
from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

print("\n" + "="*70)
print("🧪 EDEN CRITICAL GAPS - COMPREHENSIVE TEST SUITE")
print("="*70)

# ──────────────────────────────────────────────────────────────────────────
# TEST PHASE 1: ORM Methods
# ──────────────────────────────────────────────────────────────────────────

def test_phase_1_orm_imports():
    """Test that ORM methods can be imported."""
    print("\n📋 PHASE 1: Testing ORM Methods...")
    
    try:
        from eden.db.query import QuerySet
        from eden import Model
        
        # Verify methods exist
        assert hasattr(QuerySet, 'count'), "QuerySet missing count()"
        assert hasattr(QuerySet, 'get_or_404'), "QuerySet missing get_or_404()"
        assert hasattr(QuerySet, 'filter_one'), "QuerySet missing filter_one()"
        assert hasattr(QuerySet, 'get_or_create'), "QuerySet missing get_or_create()"
        assert hasattr(QuerySet, 'bulk_create'), "QuerySet missing bulk_create()"
        
        assert hasattr(Model, 'count'), "Model missing count()"
        assert hasattr(Model, 'get_or_404'), "Model missing get_or_404()"
        assert hasattr(Model, 'filter_one'), "Model missing filter_one()"
        assert hasattr(Model, 'get_or_create'), "Model missing get_or_create()"
        assert hasattr(Model, 'bulk_create'), "Model missing bulk_create()"
        
        print("  ✅ All ORM methods present")
        return True
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return False


# ──────────────────────────────────────────────────────────────────────────
# TEST PHASE 2: CSRF Fix
# ──────────────────────────────────────────────────────────────────────────

def test_phase_2_csrf_token_generation():
    """Test CSRF token generation works."""
    print("\n📋 PHASE 2: Testing CSRF Fix...")
    
    try:
        from eden.security.csrf import generate_csrf_token, get_csrf_token
        
        # Test token generation
        token1 = generate_csrf_token()
        token2 = generate_csrf_token()
        
        assert token1, "Token generation failed"
        assert token2, "Token generation failed"
        assert token1 != token2, "Tokens should be unique"
        assert len(token1) > 20, "Token too short"
        
        print("  ✅ Token generation works")
        return True
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return False


def test_phase_2_csrf_without_session():
    """Test CSRF handles missing session gracefully."""
    print("  Testing CSRF fallback (no session)...")
    
    try:
        from eden.security.csrf import get_csrf_token
        from starlette.requests import Request
        from starlette.applications import Starlette
        from starlette.testclient import TestClient
        
        app = Starlette()
        # Note: No SessionMiddleware - session unavailable
        
        @app.route("/csrf-test")
        async def csrf_test(request: Request):
            token = get_csrf_token(request)
            return JSONResponse({"token": token})
        
        client = TestClient(app)
        response = client.get("/csrf-test")
        
        assert response.status_code == 200, f"Failed with status {response.status_code}"
        data = response.json()
        assert "token" in data, "No token in response"
        assert len(data["token"]) > 20, "Token too short"
        
        print("  ✅ CSRF fallback works (no crash without session)")
        return True
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return False


def test_phase_2_csrf_with_session():
    """Test CSRF works with SessionMiddleware."""
    print("  Testing CSRF with session...")
    
    try:
        from eden.security.csrf import get_csrf_token
        from starlette.requests import Request
        from starlette.applications import Starlette
        from starlette.middleware.sessions import SessionMiddleware
        from starlette.testclient import TestClient
        from starlette.responses import JSONResponse
        
        app = Starlette()
        app.add_middleware(SessionMiddleware, secret_key="test-secret-key")
        
        @app.route("/csrf-test")
        async def csrf_test(request: Request):
            token = get_csrf_token(request)
            return JSONResponse({"token": token})
        
        client = TestClient(app)
        response = client.get("/csrf-test")
        
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert len(data["token"]) > 20
        
        # Token should be consistent across requests
        response2 = client.get("/csrf-test")
        data2 = response2.json()
        assert data["token"] == data2["token"], "Token should be consistent"
        
        print("  ✅ CSRF with session works")
        return True
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return False


# ──────────────────────────────────────────────────────────────────────────
# TEST PHASE 3: OpenAPI Documentation
# ──────────────────────────────────────────────────────────────────────────

def test_phase_3_openapi_module():
    """Test OpenAPI module imports and functions exist."""
    print("\n📋 PHASE 3: Testing OpenAPI Documentation...")
    
    try:
        from eden.openapi import (
            generate_openapi_spec,
            mount_openapi,
            _SWAGGER_HTML,
            _REDOC_HTML,
        )
        
        assert callable(generate_openapi_spec), "generate_openapi_spec not callable"
        assert callable(mount_openapi), "mount_openapi not callable"
        assert _SWAGGER_HTML, "Swagger HTML template missing"
        assert _REDOC_HTML, "ReDoc HTML template missing"
        assert "swagger-ui" in _SWAGGER_HTML.lower(), "Swagger HTML incomplete"
        assert "redoc" in _REDOC_HTML.lower(), "ReDoc HTML incomplete"
        
        print("  ✅ OpenAPI module complete")
        return True
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return False


def test_phase_3_openapi_mounting():
    """Test OpenAPI endpoints are mounted correctly."""
    print("  Testing OpenAPI endpoint mounting...")
    
    try:
        from eden.app import Eden
        from eden.openapi import mount_openapi
        
        app = Eden(title="Test API", version="1.0.0", description="Test")
        
        # Define a test route
        @app.get("/hello/{name}")
        async def hello(name: str):
            """Greet a person."""
            return {"message": f"Hello, {name}!"}
        
        # Mount OpenAPI
        mount_openapi(app)
        
        # Verify routes were added
        routes = [route.name for route in app._router.routes if hasattr(route, 'name')]
        
        assert "openapi_spec" in routes, "openapi_spec route not mounted"
        assert "swagger_ui" in routes, "swagger_ui route not mounted"
        assert "redoc_ui" in routes, "redoc_ui route not mounted"
        
        print("  ✅ OpenAPI endpoints mounted")
        return True
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return False


def test_phase_3_openapi_spec_generation():
    """Test OpenAPI spec generation works."""
    print("  Testing OpenAPI spec generation...")
    
    try:
        from eden.app import Eden
        from eden.openapi import generate_openapi_spec
        
        app = Eden(title="Test API", version="1.0.0")
        
        @app.get("/users/{user_id}")
        async def get_user(user_id: int):
            """Get a user by ID."""
            return {"id": user_id}
        
        @app.post("/users")
        async def create_user(name: str, email: str):
            """Create a new user."""
            return {"name": name, "email": email}
        
        spec = generate_openapi_spec(app)
        
        assert spec["openapi"] == "3.1.0", "Wrong OpenAPI version"
        assert spec["info"]["title"] == "Test API", "Wrong title"
        assert spec["info"]["version"] == "1.0.0", "Wrong version"
        assert "paths" in spec, "Missing paths in spec"
        
        print("  ✅ OpenAPI spec generation works")
        return True
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return False


# ──────────────────────────────────────────────────────────────────────────
# SUMMARY
# ──────────────────────────────────────────────────────────────────────────

def run_all_tests():
    """Run all tests and report results."""
    results = []
    
    # Phase 1
    results.append(("Phase 1: ORM Methods Import", test_phase_1_orm_imports()))
    
    # Phase 2
    results.append(("Phase 2: CSRF Token Generation", test_phase_2_csrf_token_generation()))
    results.append(("Phase 2: CSRF Without Session", test_phase_2_csrf_without_session()))
    results.append(("Phase 2: CSRF With Session", test_phase_2_csrf_with_session()))
    
    # Phase 3
    results.append(("Phase 3: OpenAPI Module", test_phase_3_openapi_module()))
    results.append(("Phase 3: OpenAPI Mounting", test_phase_3_openapi_mounting()))
    results.append(("Phase 3: OpenAPI Spec Generation", test_phase_3_openapi_spec_generation()))
    
    # Print summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print("="*70)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! All 3 phases working correctly.")
    else:
        print(f"⚠️  {total - passed} test(s) failed. Review above.")
    
    print("="*70 + "\n")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
