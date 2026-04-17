"""
Tests for consolidated framework-native admin dashboard authentication.

Verifies:
1. Native user authentication for admin routes
2. JWT and Session integration
3. Role mapping (Staff/Superuser -> Admin/Editor/Viewer)
4. Protected API endpoints (/api/me, /api/flags)
"""

import pytest
from httpx import AsyncClient, ASGITransport
from datetime import datetime

from eden import Eden
from eden.auth.models import User
from eden.auth.actions import create_user
from eden.admin import admin as admin_site

# =====================================================================
# Fixtures
# =====================================================================

@pytest.fixture
async def app():
    """Create Eden app with native admin auth and working sessions."""
    from eden.config import Config
    from eden.db.session import init_db
    
    config = Config(
        env="dev",
        secret_key="test-secret-key-long-enough-for-jwt-32-chars",
        debug=True,
        database_url="sqlite+aiosqlite:///:memory:"
    )
    
    app = Eden(
        config=config,
        admin_enabled=True
    )
    
    # Initialize and connect database
    init_db(config.database_url, app=app)
    await app.state.db.connect(create_tables=True)
    
    # Add native admin routes
    app.include_router(admin_site.build_router(prefix="/admin"))
    
    # Force adding SessionMiddleware because Eden's setup_defaults disables it in test mode.
    # We want to test session-based login.
    app.add_middleware("session", priority=app.PRIORITY_CORE + 20, secret_key=config.secret_key, https_only=False)
    
    # Build to initialize internal components (includes setup_defaults)
    await app.build()
    
    return app

@pytest.fixture
async def client(app):
    """Create async test client."""
    starlette_app = await app.build()
    transport = ASGITransport(app=starlette_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c

@pytest.fixture
async def admin_user(app):
    """Create a superuser."""
    return await create_user(
        email=f"admin_{datetime.now().timestamp()}@example.com",
        password="StrongPassw0rd!",
        is_superuser=True
    )

@pytest.fixture
async def editor_user(app):
    """Create a staff user (editor)."""
    return await create_user(
        email=f"editor_{datetime.now().timestamp()}@example.com",
        password="StrongPassw0rd!",
        is_staff=True
    )

@pytest.fixture
async def viewer_user(app):
    """Create a regular user (viewer)."""
    return await create_user(
        email=f"viewer_{datetime.now().timestamp()}@example.com",
        password="StrongPassw0rd!"
    )

# =====================================================================
# Authentication Tests
# =====================================================================

@pytest.mark.asyncio
async def test_admin_login_redirect_with_token(client, admin_user):
    """Test successful login redirects with a JWT token."""
    response = await client.post("/admin/login", data={
        "email": admin_user.email,
        "password": "StrongPassw0rd!"
    })
    
    assert response.status_code == 303
    assert "token=" in response.headers["location"]
    # Check that session cookie is also set
    assert "session" in response.cookies

@pytest.mark.asyncio
async def test_api_me_with_session(client, admin_user):
    """Test /api/me works with session-based auth."""
    # Login to set session
    await client.post("/admin/login", data={
        "email": admin_user.email,
        "password": "StrongPassw0rd!"
    })
    
    response = await client.get("/admin/api/me")
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == admin_user.email
    assert data["role"] == "admin"

@pytest.mark.asyncio
async def test_api_me_with_jwt(client, admin_user, app):
    """Test /api/me works with JWT auth."""
    # Generate token manually or via login redirect
    from eden.auth.backends.jwt import JWTBackend
    jwt_backend = JWTBackend(secret_key="test-secret-key-long-enough-for-jwt-32-chars")
    token = jwt_backend.create_access_token({"sub": str(admin_user.id)})
    
    response = await client.get(
        "/admin/api/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["username"] == admin_user.email

@pytest.mark.asyncio
async def test_role_mapping(client, editor_user, viewer_user):
    """Test that core user roles map correctly to admin roles."""
    # Editor (Staff)
    await client.post("/admin/login", data={
        "email": editor_user.email,
        "password": "StrongPassw0rd!"
    })
    resp = await client.get("/admin/api/me")
    assert resp.status_code == 200
    assert resp.json()["role"] == "editor"
    
    # Logout
    await client.post("/admin/api/logout")
    
    # Viewer (General user) -> Should be rejected
    await client.post("/admin/login", data={
        "email": viewer_user.email,
        "password": "StrongPassw0rd!"
    })
    # Note: admin_login views.py redirects to login page with error if not staff
    # but /api/me checks _check_staff and raises Forbidden
    resp = await client.get("/admin/api/me")
    assert resp.status_code == 403

@pytest.mark.asyncio
async def test_logout(client, admin_user):
    """Test logout clears the session."""
    await client.post("/admin/login", data={
        "email": admin_user.email,
        "password": "StrongPassw0rd!"
    })
    
    # Post to logout
    response = await client.post("/admin/api/logout")
    assert response.status_code == 200
    
    # Try to access protected route
    response = await client.get("/admin/api/me")
    assert response.status_code == 401
