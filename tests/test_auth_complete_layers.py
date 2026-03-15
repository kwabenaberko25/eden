"""
Comprehensive Auth System Tests — All Layers

Tests the complete authentication system:
- Layer 1: User Model (BaseUser, User, SocialAccount)
- Layer 2: Password Hashing (Argon2)
- Layer 3: Query-Level RBAC
- Layer 4: OAuth Providers
- Layer 5: Middleware & Dependencies

This test suite validates end-to-end integration across all layers.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

# ── Layer 1: User Model Tests ────────────────────────────────────────────

def test_baseuser_password_hashing():
    """Verify BaseUser password hashing methods."""
    from eden.auth.models import User
    
    user = User(email="alice@example.com")
    user.set_password("secret123")
    
    # Hashed password should not match plaintext
    assert user.password_hash != "secret123"
    assert user.password_hash.startswith("$argon2id$")
    
    # Check password should work
    assert user.check_password("secret123") is True
    assert user.check_password("wrong") is False


def test_baseuser_roles_and_permissions():
    """Verify BaseUser roles and permissions storage."""
    from eden.auth.models import User
    
    user = User(email="bob@example.com")
    user.roles = ["admin", "moderator"]
    user.permissions = ["view_users", "edit_users", "delete_users"]
    
    assert "admin" in user.roles
    assert "view_users" in user.permissions
    # is_superuser has default=False by SQLAlchemy definition
    assert getattr(user, "is_superuser", False) is not True
    assert getattr(user, "is_staff", False) is not True


def test_baseuser_repr():
    """Verify BaseUser string representation."""
    from eden.auth.models import User
    
    user = User(email="charlie@example.com")
    repr_str = repr(user)
    
    assert "User" in repr_str
    assert "charlie@example.com" in repr_str


# ── Layer 2: Password Hashing Tests ──────────────────────────────────────

def test_password_hashing_functions():
    """Verify hash_password and check_password functions."""
    from eden.auth.hashers import hash_password, check_password
    
    password = "my-secure-password-2024"
    hashed = hash_password(password)
    
    # Hash should be different each time (salt)
    hashed2 = hash_password(password)
    assert hashed != hashed2
    
    # But both should verify correctly
    assert check_password(password, hashed) is True
    assert check_password(password, hashed2) is True
    assert check_password("wrong", hashed) is False


def test_argon2_hasher_needs_rehash():
    """Verify Argon2 hasher rehash detection."""
    from eden.auth.hashers import Argon2Hasher, hasher
    
    password = "test-password"
    hashed = hasher.hash(password)
    
    # Fresh hashes don't need rehashing
    assert hasher.needs_rehash(hashed) is False


# ── Layer 3: Query-Level RBAC Tests ──────────────────────────────────────

def test_user_has_permission():
    """Verify user_has_permission query helper."""
    from eden.auth.query_filtering import user_has_permission
    
    class MockUser:
        def __init__(self, permissions=None, is_superuser=False):
            self.permissions = permissions or []
            self.is_superuser = is_superuser
    
    # Regular user with permission
    user = MockUser(permissions=["delete_posts"])
    assert user_has_permission(user, "delete_posts") is True
    assert user_has_permission(user, "edit_posts") is False
    
    # Superuser has all permissions
    superuser = MockUser(is_superuser=True)
    assert user_has_permission(superuser, "anything") is True


def test_user_has_role():
    """Verify user_has_role query helper."""
    from eden.auth.query_filtering import user_has_role
    
    class MockUser:
        def __init__(self, roles=None, is_superuser=False):
            self.roles = roles or []
            self.is_superuser = is_superuser
    
    # Regular user with role
    user = MockUser(roles=["editor"])
    assert user_has_role(user, "editor") is True
    assert user_has_role(user, "admin") is False
    
    # Superuser has all roles
    superuser = MockUser(is_superuser=True)
    assert user_has_role(superuser, "any_role") is True


def test_user_has_any_permission():
    """Verify user_has_any_permission query helper."""
    from eden.auth.query_filtering import user_has_any_permission
    
    class MockUser:
        def __init__(self, permissions=None, is_superuser=False):
            self.permissions = permissions or []
            self.is_superuser = is_superuser
    
    user = MockUser(permissions=["read", "write"])
    
    # Has at least one
    assert user_has_any_permission(user, "read", "execute") is True
    
    # Has none
    assert user_has_any_permission(user, "delete", "execute") is False
    
    # Superuser has any
    superuser = MockUser(is_superuser=True)
    assert user_has_any_permission(superuser, "anything") is True


def test_user_has_any_role():
    """Verify user_has_any_role query helper."""
    from eden.auth.query_filtering import user_has_any_role
    
    class MockUser:
        def __init__(self, roles=None, is_superuser=False):
            self.roles = roles or []
            self.is_superuser = is_superuser
    
    user = MockUser(roles=["editor", "contributor"])
    
    # Has at least one
    assert user_has_any_role(user, "admin", "editor") is True
    
    # Has none
    assert user_has_any_role(user, "admin", "moderator") is False


# ── Layer 4: OAuth Provider Tests ────────────────────────────────────────

def test_oauth_provider_creation():
    """Verify OAuthProvider dataclass creation."""
    from eden.auth.oauth import OAuthProvider
    
    provider = OAuthProvider(
        name="google",
        client_id="123456",
        client_secret="secret123",
        authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        userinfo_url="https://www.googleapis.com/oauth2/v2/userinfo",
        scopes=["openid", "email", "profile"],
    )
    
    assert provider.name == "google"
    assert provider.client_id == "123456"
    assert len(provider.scopes) == 3


def test_oauth_manager_register_google():
    """Verify OAuthManager Google registration."""
    from eden.auth.oauth import OAuthManager
    
    oauth = OAuthManager()
    oauth.register_google(
        client_id="google-123",
        client_secret="google-secret",
    )
    
    assert "google" in oauth._providers
    provider = oauth._providers["google"]
    assert provider.client_id == "google-123"


def test_oauth_manager_register_github():
    """Verify OAuthManager GitHub registration."""
    from eden.auth.oauth import OAuthManager
    
    oauth = OAuthManager()
    oauth.register_github(
        client_id="github-123",
        client_secret="github-secret",
    )
    
    assert "github" in oauth._providers
    provider = oauth._providers["github"]
    assert provider.client_id == "github-123"


# ── Layer 5: Middleware & Dependencies Tests ─────────────────────────────

@pytest.mark.asyncio
async def test_jwt_backend_creates_tokens():
    """Verify JWTBackend token creation."""
    from eden.auth.backends.jwt import JWTBackend
    import jwt
    
    backend = JWTBackend(secret_key="test-secret")
    data = {"sub": "user-123", "name": "Alice"}
    
    access_token = backend.create_access_token(data)
    refresh_token = backend.create_refresh_token(data)
    
    assert access_token != refresh_token
    
    # Decode and verify
    decoded_access = jwt.decode(access_token, "test-secret", algorithms=["HS256"])
    assert decoded_access["sub"] == "user-123"
    assert decoded_access["type"] == "access"
    
    decoded_refresh = jwt.decode(refresh_token, "test-secret", algorithms=["HS256"])
    assert decoded_refresh["type"] == "refresh"


@pytest.mark.asyncio
async def test_session_backend_login_logout():
    """Verify SessionBackend login/logout operations."""
    from eden.auth.backends.session import SessionBackend
    
    backend = SessionBackend()
    
    # Mock request with session
    request = MagicMock()
    request.session = {}
    
    # Mock user
    user = MagicMock()
    user.id = 42
    
    # Login
    await backend.login(request, user)
    assert request.session["_auth_user_id"] == "42"
    
    # Logout
    await backend.logout(request)
    assert "_auth_user_id" not in request.session


@pytest.mark.asyncio
async def test_api_key_backend_extraction():
    """Verify APIKeyBackend key extraction."""
    from eden.auth.backends.api_key import APIKeyBackend
    
    backend = APIKeyBackend()
    
    # Test Bearer token extraction
    request = MagicMock()
    request.headers = {"Authorization": "Bearer eden_abc123xyz"}
    
    key = backend._extract_key(request)
    assert key == "eden_abc123xyz"
    
    # Test X-API-Key header extraction
    request2 = MagicMock()
    request2.headers = {"X-API-Key": "eden_def456uvw", "Authorization": ""}
    
    key2 = backend._extract_key(request2)
    assert key2 == "eden_def456uvw"
    
    # Test no key
    request3 = MagicMock()
    request3.headers = {}
    
    key3 = backend._extract_key(request3)
    assert key3 is None


# ── Decorators Tests ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_required_decorator():
    """Verify login_required decorator."""
    from eden.auth.decorators import login_required
    from eden.exceptions import Unauthorized
    
    @login_required
    async def protected_view(request):
        return {"message": "success"}
    
    # Mock request without user
    request = MagicMock(user=None)
    request.state = MagicMock(user=None)
    request.headers = {}
    request.scope = {"type": "http"}
    
    with pytest.raises(Unauthorized):
        await protected_view(request=request)


@pytest.mark.asyncio
async def test_roles_required_decorator():
    """Verify roles_required decorator."""
    from eden.auth.decorators import roles_required
    from eden.exceptions import Forbidden
    
    @roles_required(["admin"])
    async def admin_view(request):
        return {"message": "admin"}
    
    # Mock request with non-admin user
    request = MagicMock()
    request.state = MagicMock()
    
    user = MagicMock()
    user.roles = ["user"]
    user.is_superuser = False
    request.state.user = user
    request.headers = {}
    request.scope = {"type": "http"}
    
    with pytest.raises(Forbidden):
        await admin_view(request=request)


@pytest.mark.asyncio
async def test_permission_required_decorator():
    """Verify require_permission decorator."""
    from eden.auth.decorators import require_permission
    from eden.exceptions import Forbidden
    
    @require_permission("edit_posts")
    async def edit_view(request):
        return {"message": "edited"}
    
    # Mock request with user lacking permission
    request = MagicMock()
    request.state = MagicMock()
    
    user = MagicMock()
    user.permissions = ["view_posts"]
    user.roles = []
    user.is_superuser = False
    request.state.user = user
    request.headers = {}
    request.scope = {"type": "http"}
    
    with pytest.raises(Forbidden):
        await edit_view(request=request)


@pytest.mark.asyncio
async def test_is_authorized_decorator():
    """Verify is_authorized decorator."""
    from eden.auth.decorators import is_authorized
    from eden.exceptions import Unauthorized
    
    @is_authorized
    async def authorized_view(request):
        return {"message": "authorized"}
    
    # Mock request without user
    request = MagicMock(user=None)
    request.state = MagicMock(user=None)
    request.headers = {}
    request.scope = {"type": "http"}
    
    with pytest.raises(Unauthorized):
        await authorized_view(request=request)


# ── Integration Tests ────────────────────────────────────────────────────

def test_rbac_hierarchy():
    """Verify RBAC role hierarchy."""
    from eden.auth.rbac import EdenRBAC
    
    rbac = EdenRBAC()
    
    # Create role hierarchy
    rbac.add_role("user")
    rbac.add_role("moderator", parents=["user"])
    rbac.add_role("admin", parents=["moderator"])
    
    # Add permissions
    rbac.add_permission("user", "read")
    rbac.add_permission("moderator", "edit")
    rbac.add_permission("admin", "delete")
    
    # Check inheritance
    assert rbac.has_permission(["user"], "read") is True
    assert rbac.has_permission(["moderator"], "read") is True  # Inherits from user
    assert rbac.has_permission(["moderator"], "edit") is True
    assert rbac.has_permission(["admin"], "read") is True  # Inherits through moderator
    assert rbac.has_permission(["admin"], "edit") is True
    assert rbac.has_permission(["admin"], "delete") is True


def test_apikey_prefix_obfuscation():
    """Verify API key prefix obfuscation."""
    from eden.auth.api_key_model import APIKey
    
    # When creating a key, only the prefix is stored
    # The full key is returned once and not stored anywhere
    assert hasattr(APIKey, "generate")
    assert hasattr(APIKey, "prefix")
    assert hasattr(APIKey, "key_hash")
    assert hasattr(APIKey, "is_valid")


# ── Export Tests ────────────────────────────────────────────────────────

def test_auth_module_exports():
    """Verify all auth components are properly exported."""
    from eden import auth
    
    # Layer 1: Models
    assert hasattr(auth, "User")
    assert hasattr(auth, "BaseUser")
    assert hasattr(auth, "SocialAccount")
    assert hasattr(auth, "APIKey")
    
    # Layer 2: Password Hashing
    assert hasattr(auth, "hash_password")
    assert hasattr(auth, "check_password")
    assert hasattr(auth, "Argon2Hasher")
    
    # Layer 3: Query-Level RBAC
    assert hasattr(auth, "apply_rbac_filter")
    assert hasattr(auth, "user_has_permission")
    assert hasattr(auth, "user_has_role")
    assert hasattr(auth, "user_has_any_permission")
    assert hasattr(auth, "user_has_any_role")
    
    # Layer 4: OAuth
    assert hasattr(auth, "OAuthManager")
    assert hasattr(auth, "OAuthProvider")
    
    # Layer 5: Middleware & Decorators
    assert hasattr(auth, "AuthenticationMiddleware")
    assert hasattr(auth, "login_required")
    assert hasattr(auth, "roles_required")
    assert hasattr(auth, "permissions_required")
    assert hasattr(auth, "require_permission")
    assert hasattr(auth, "is_authorized")
    assert hasattr(auth, "bind_user_principal")
    
    # Layer 5: Backends
    assert hasattr(auth, "AuthBackend")
    assert hasattr(auth, "JWTBackend")
    assert hasattr(auth, "SessionBackend")
    assert hasattr(auth, "APIKeyBackend")
    assert hasattr(auth, "get_current_user")
    assert hasattr(auth, "current_user")
    
    # Layer 4: Providers
    assert hasattr(auth, "JWTProvider")
    
    # RBAC
    assert hasattr(auth, "default_rbac")
    assert hasattr(auth, "EdenRBAC")
