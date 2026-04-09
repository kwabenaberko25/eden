"""
Tests for admin dashboard authentication.

Verifies:
1. User registration and authentication
2. Token creation and verification
3. Role-based access control
4. Login attempt rate limiting
5. Protected endpoints
"""


import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from eden import Eden, Depends

from eden.admin.auth import AdminAuthManager, AdminRole, AdminUser
from eden.admin.auth_routes import get_protected_admin_routes
from eden.admin.login_template import LoginPageTemplate


# =====================================================================
# Fixtures
# =====================================================================

@pytest.fixture
def auth_manager():
    """Create auth manager instance."""
    return AdminAuthManager(secret_key="test-secret-key-32-characters-long!!!")


@pytest.fixture
def app_with_auth(auth_manager):
    """Create Eden app with auth."""
    app = Eden(secret_key="test-secret-key-long-enough-for-jwt-32-chars")
    
    # Register test users
    auth_manager.register_user("admin", "StrongPassw0rd!", AdminRole.ADMIN)
    auth_manager.register_user("editor", "StrongPassw0rd!", AdminRole.EDITOR)
    auth_manager.register_user("viewer", "StrongPassw0rd!", AdminRole.VIEWER)
    
    # Add routes
    app.include_router(get_protected_admin_routes(auth_manager))
    
    return app


@pytest.fixture
async def client(app_with_auth):
    """Create async test client."""
    starlette_app = await app_with_auth.build()
    transport = ASGITransport(app=starlette_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


# =====================================================================
# User Registration Tests
# =====================================================================

def test_register_user(auth_manager):
    """Test user registration."""
    user = auth_manager.register_user("alice", "StrongPassw0rd!", AdminRole.VIEWER)
    
    assert user.username == "alice"
    assert user.role == AdminRole.VIEWER
    assert user.is_active


def test_register_duplicate_user(auth_manager):
    """Test that duplicate registration fails."""
    auth_manager.register_user("alice", "StrongPassw0rd!")
    
    with pytest.raises(ValueError):
        auth_manager.register_user("alice", "different")


def test_list_users(auth_manager):
    """Test listing users."""
    auth_manager.register_user("alice", "StrongPassw0rd!", AdminRole.ADMIN)
    auth_manager.register_user("bob", "StrongPassw0rd!", AdminRole.EDITOR)
    
    users = auth_manager.list_users()
    assert len(users) == 2


# =====================================================================
# Password Tests
# =====================================================================

def test_password_hashing(auth_manager):
    """Test password hashing."""
    password = "StrongPassw0rd!"
    hash1 = auth_manager._hash_password(password)
    hash2 = auth_manager._hash_password(password)
    
    # Argon2 hashes are non-deterministic, so we test verification instead
    assert auth_manager.verify_password(password, hash1)
    assert auth_manager.verify_password(password, hash2)
    assert password not in hash1


def test_verify_password(auth_manager):
    """Test password verification."""
    password = "StrongPassword123!"
    wrong = "WrongPassword456!"
    
    hash_val = auth_manager._hash_password(password)
    
    assert auth_manager.verify_password(password, hash_val)
    assert not auth_manager.verify_password(wrong, hash_val)


def test_change_password(auth_manager):
    """Test password change."""
    auth_manager.register_user("alice", "StrongPassw0rd!")
    
    # Change password
    auth_manager.change_password("alice", "StrongPassw0rd!", "NewStr0ngP@ss123!")
    
    # Old password should fail
    with pytest.raises(ValueError):
        auth_manager.change_password("alice", "StrongPassw0rd!", "AnotherPass123!")
    
    # New password should work
    auth_manager.change_password("alice", "NewStr0ngP@ss123!", "ThirdPass123!")


def test_change_password_nonexistent_user(auth_manager):
    """Test changing password for non-existent user."""
    with pytest.raises(ValueError):
        auth_manager.change_password("nobody", "old", "new")


# =====================================================================
# Authentication Tests
# =====================================================================

def test_login_success(auth_manager):
    """Test successful login."""
    auth_manager.register_user("alice", "StrongPassw0rd!")
    
    token = auth_manager.login("alice", "StrongPassw0rd!")
    
    assert token is not None
    assert len(token) > 20  # JWT tokens are long


def test_login_wrong_password(auth_manager):
    """Test login with wrong password."""
    auth_manager.register_user("alice", "Correct123!@")
    
    with pytest.raises(Exception):
        auth_manager.login("alice", "WrongPass456!")


def test_login_nonexistent_user(auth_manager):
    """Test login for non-existent user."""
    with pytest.raises(Exception):
        auth_manager.login("nobody", "StrongPassw0rd!")


def test_login_inactive_user(auth_manager):
    """Test login for inactive user."""
    user = auth_manager.register_user("alice", "StrongPassw0rd!")
    user.is_active = False
    
    with pytest.raises(Exception):
        auth_manager.login("alice", "StrongPassw0rd!")


# =====================================================================
# Token Tests
# =====================================================================

def test_create_jwt_token(auth_manager):
    """Test JWT token creation."""
    user = auth_manager.register_user("alice", "StrongPassw0rd!", AdminRole.ADMIN)
    token = auth_manager._create_jwt_token(user)
    
    assert token is not None
    assert "." in token  # JWT format: header.payload.signature


def test_verify_token(auth_manager):
    """Test token verification."""
    user = auth_manager.register_user("alice", "StrongPassw0rd!")
    token = auth_manager._create_jwt_token(user)
    
    payload = auth_manager.verify_token(token)
    
    assert payload["username"] == "alice"
    assert payload["role"] == "viewer"


def test_verify_invalid_token(auth_manager):
    """Test verification of invalid token."""
    with pytest.raises(Exception):
        auth_manager.verify_token("invalid.token.here")


def test_get_current_user(auth_manager):
    """Test getting user from token."""
    auth_manager.register_user("alice", "StrongPassw0rd!", AdminRole.EDITOR)
    token = auth_manager.login("alice", "StrongPassw0rd!")
    
    user = auth_manager.get_current_user(token)
    
    assert user.username == "alice"
    assert user.role == AdminRole.EDITOR


# =====================================================================
# Session Tests
# =====================================================================

def test_login_creates_session(auth_manager):
    """Test that login creates a session."""
    auth_manager.register_user("alice", "StrongPassw0rd!")
    
    initial_sessions = len(auth_manager.sessions)
    token = auth_manager.login("alice", "StrongPassw0rd!")
    
    assert len(auth_manager.sessions) == initial_sessions + 1
    assert token in auth_manager.sessions


def test_logout(auth_manager):
    """Test logout."""
    auth_manager.register_user("alice", "StrongPassw0rd!")
    token = auth_manager.login("alice", "StrongPassw0rd!")
    
    auth_manager.logout(token)
    
    assert token not in auth_manager.sessions


def test_logout_all_sessions(auth_manager):
    """Test logout all sessions for user."""
    auth_manager.register_user("alice", "StrongPassw0rd!")
    
    token1 = auth_manager.login("alice", "StrongPassw0rd!")
    # Add small delay to ensure different JWT tokens
    import time
    time.sleep(0.01)
    token2 = auth_manager.login("alice", "StrongPassw0rd!")
    
    # Ensure tokens are different
    assert token1 != token2, "Tokens should be different"
    
    count = auth_manager.logout_all("alice")
    
    assert count == 2
    assert token1 not in auth_manager.sessions
    assert token2 not in auth_manager.sessions


# =====================================================================
# Rate Limiting Tests
# =====================================================================

def test_login_lockout_after_failed_attempts(auth_manager):
    """Test lockout after too many failed attempts."""
    auth_manager.register_user("alice", "Correct123!@")
    
    # Make failed attempts
    failed_count = 0
    for i in range(5):
        try:
            auth_manager.login("alice", "wrong")
        except Exception:
            failed_count += 1
    
    # Should have had failed attempts
    assert failed_count == 5


def test_lockout_duration(auth_manager):
    """Test that lockout logic is tracked."""
    auth_manager.register_user("alice", "StrongPassw0rd!")
    
    # Cause failed attempts
    for i in range(5):
        try:
            auth_manager.login("alice", "wrong")
        except Exception:
            pass
    
    # Check that user is locked out after max attempts
    with pytest.raises(Exception):  # Should raise HTTPException for locked out user
        auth_manager.login("alice", "StrongPassw0rd!")


# =====================================================================
# Role-Based Access Control Tests
# =====================================================================

def test_admin_role(auth_manager):
    """Test ADMIN role."""
    auth_manager.register_user("alice", "StrongPassw0rd!", AdminRole.ADMIN)
    user = auth_manager.get_user("alice")
    
    assert user.role == AdminRole.ADMIN


def test_editor_role(auth_manager):
    """Test EDITOR role."""
    auth_manager.register_user("bob", "StrongPassw0rd!", AdminRole.EDITOR)
    user = auth_manager.get_user("bob")
    
    assert user.role == AdminRole.EDITOR


def test_update_user_role(auth_manager):
    """Test updating user role."""
    auth_manager.register_user("alice", "StrongPassw0rd!", AdminRole.VIEWER)
    
    auth_manager.update_user_role("alice", AdminRole.ADMIN)
    
    user = auth_manager.get_user("alice")
    assert user.role == AdminRole.ADMIN


# =====================================================================
# HTTP Tests (Protected Endpoints)
# =====================================================================

@pytest.mark.asyncio
async def test_login_endpoint(client):
    """Test POST /admin/api/login."""
    response = await client.post("/admin/api/login", json={
        "username": "admin",
        "password": "StrongPassw0rd!"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["username"] == "admin"


@pytest.mark.asyncio
async def test_login_wrong_credentials(client):
    """Test login with wrong credentials."""
    response = await client.post("/admin/api/login", json={
        "username": "admin",
        "password": "wrong"
    })
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_dashboard_requires_auth(client):
    """Test that dashboard requires authentication."""
    response = await client.get("/admin/")
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_dashboard_with_auth(client):
    """Test dashboard with valid token."""
    # Login
    login_response = await client.post("/admin/api/login", json={
        "username": "admin",
        "password": "StrongPassw0rd!"
    })
    token = login_response.json()["access_token"]
    
    # Access dashboard
    response = await client.get(
        "/admin/",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    assert "Feature Flags Admin" in response.text


@pytest.mark.asyncio
async def test_logout_endpoint(client):
    """Test POST /admin/api/logout."""
    # Login
    login_response = await client.post("/admin/api/login", json={
        "username": "admin",
        "password": "StrongPassw0rd!"
    })
    token = login_response.json()["access_token"]
    
    # Logout
    response = await client.post(
        "/admin/api/logout",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    assert response.json()["status"] == "logged_out"


@pytest.mark.asyncio
async def test_get_current_user_endpoint(client):
    """Test GET /admin/api/me."""
    # Login
    login_response = await client.post("/admin/api/login", json={
        "username": "editor",
        "password": "StrongPassw0rd!"
    })
    token = login_response.json()["access_token"]
    
    # Get current user
    response = await client.get(
        "/admin/api/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "editor"
    assert data["role"] == "editor"


# =====================================================================
# Login Page Tests
# =====================================================================

def test_login_page_renders():
    """Test that login page renders."""
    html = LoginPageTemplate.render()
    
    assert html.startswith("<!DOCTYPE html>")
    assert "Admin Login" in html
    assert "username" in html
    assert "password" in html.lower()  # Check for password field


def test_login_page_offline_capable():
    """Test that login page has no external dependencies."""
    html = LoginPageTemplate.render()
    
    assert "cdn.jsdelivr.net" not in html
    assert "bootstrap" not in html
    assert "<style>" in html
    assert "<script>" in html


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
