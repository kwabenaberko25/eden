import asyncio
import uuid
from typing import Any
from unittest.mock import MagicMock, AsyncMock

# Mocking Eden dependencies for standalone verification
from eden.requests import Request
from eden.responses import JsonResponse, RedirectResponse
from eden.auth.backends.jwt import JWTBackend
from eden.security.urls import is_safe_url
from eden.admin import AdminSite

async def verify_jwt_cookie():
    print("--- Verifying JWT Cookie Support ---")
    secret = "test-secret"
    backend = JWTBackend(secret_key=secret)
    
    # Create a token
    token = backend.create_access_token({"sub": "user_123"})
    
    # Mock request with cookie but no header
    headers = {}
    cookies = {"access_token": token}
    request = MagicMock(spec=Request)
    request.headers = headers
    request.cookies = cookies
    
    # Mock decoded result
    user = await backend.authenticate(request)
    assert user is not None
    assert str(user.id) == "user_123"
    print("✅ JWT successfully extracted from cookie")

async def verify_safe_redirect():
    print("\n--- Verifying Safe Redirects ---")
    request = MagicMock(spec=Request)
    request.headers = {"host": "localhost:8000"}
    
    assert is_safe_url("/admin/", request) is True
    assert is_safe_url("https://malicious.com", request) is False
    assert is_safe_url("//malicious.com", request) is False
    assert is_safe_url("http://localhost:8000/admin/", request) is True
    print("✅ URL safety validation working correctly")

async def verify_admin_login_refactor():
    print("\n--- Verifying Admin Login Refactor ---")
    from eden.admin.views import admin_login
    
    # Mock request
    request = MagicMock(spec=Request)
    request.method = "POST"
    request.url.scheme = "http"
    request.query_params = {"next": "/admin/custom"}
    
    async def mock_form():
        return {"email": "admin@example.com", "password": "password"}
    request.form = mock_form
    
    # Mock authentication
    with MagicMock() as mock_auth:
        import eden.auth.actions
        user = MagicMock()
        user.id = uuid.uuid4()
        user.is_staff = True
        user.is_superuser = True
        
        # Patch authenticate
        original_auth = eden.auth.actions.authenticate
        async def mock_authenticate(*args, **kwargs): return user
        eden.auth.actions.authenticate = mock_authenticate
        
        # Patch secret key helper
        import eden.admin.views
        async def mock_secret(req): return "secret"
        eden.admin.views._get_secret_key = mock_secret
        
        response = await admin_login(request, MagicMock())
        
        assert isinstance(response, RedirectResponse)
        assert "token=" not in response.headers["location"]
        assert "access_token=" in response.headers.get("set-cookie", "")
        print("✅ Login sets cookie and doesn't leak token in URL")
        
        # Restore
        eden.auth.actions.authenticate = original_auth

async def verify_global_tenancy():
    print("\n--- Verifying Global Tenancy for Superusers ---")
    from eden.tenancy.context import is_across_tenants
    from eden.admin import require_admin
    
    @require_admin
    async def dummy_admin_view(request):
        return is_across_tenants()

    # Case 1: Superuser
    super_user = MagicMock()
    super_user.is_superuser = True
    super_user.is_staff = True
    
    req = MagicMock(spec=Request)
    req.state = MagicMock()
    req.state.user = super_user
    
    result = await dummy_admin_view(req)
    assert result is True
    print("✅ Superuser view runs AcrossTenants=True")
    
    # Case 2: Regular Staff
    staff_user = MagicMock()
    staff_user.is_superuser = False
    staff_user.is_staff = True
    
    req.state.user = staff_user
    result = await dummy_admin_view(req)
    assert result is False
    print("✅ Regular staff view runs AcrossTenants=False")

if __name__ == "__main__":
    async def main():
        await verify_jwt_cookie()
        await verify_safe_redirect()
        await verify_admin_login_refactor()
        await verify_global_tenancy()
        print("\n✨ ALL VERIFICATIONS PASSED ✨")
    
    asyncio.run(main())
