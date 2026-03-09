import pytest
import jwt
from eden.auth.hashers import hash_password, check_password, hasher
from eden.auth.models import User
from eden.auth.backends.jwt import JWTBackend
from eden.auth.backends.session import SessionBackend
from eden.auth.decorators import login_required, roles_required, permissions_required
from eden.requests import Request
from eden.exceptions import Unauthorized, Forbidden

def test_password_hashing():
    password = "secret-password"
    hashed = hash_password(password)
    
    assert hashed != password
    assert check_password(password, hashed) is True
    assert check_password("wrong-password", hashed) is False

def test_hasher_needs_rehash():
    # Argon2 hashes usually don't need rehash immediately with default settings
    hashed = hash_password("test")
    assert hasher.needs_rehash(hashed) is False

def test_user_model_password():
    user = User(email="test@eden.dev")
    user.set_password("eden-rocks")
    
    assert user.password_hash.startswith("$argon2id$")
    assert user.check_password("eden-rocks") is True
    assert user.check_password("wrong") is False

@pytest.mark.asyncio
async def test_jwt_backend_tokens():
    backend = JWTBackend(secret_key="test-secret")
    data = {"sub": "user-123", "name": "Alice"}
    
    access_token = backend.create_access_token(data)
    refresh_token = backend.create_refresh_token(data)
    
    assert access_token != refresh_token
    
    decoded = backend.decode_token(access_token)
    assert decoded["sub"] == "user-123"
    assert decoded["type"] == "access"
    
    decoded_refresh = backend.decode_token(refresh_token)
    assert decoded_refresh["type"] == "refresh"

@pytest.mark.asyncio
async def test_auth_decorators_logic():
    # Mocking a request and user
    class MockUser:
        def __init__(self, roles=None, permissions=None, is_superuser=False):
            self.roles = roles or []
            self.permissions = permissions or []
            self.is_superuser = is_superuser
    
    async def mock_view(request):
        return "OK"

    # 1. Login Required
    decorated_login = login_required(mock_view)
    
    # Mock request without user
    class MockRequest:
        def __init__(self, user=None):
            self.state = type("state", (), {"user": user})()
            self.scope = {"type": "http"}
            self.headers = {}
    
    req_no_user = MockRequest(user=None)
    with pytest.raises(Unauthorized):
        await decorated_login(request=req_no_user)
    
    req_with_user = MockRequest(user=MockUser())
    assert await decorated_login(request=req_with_user) == "OK"

    # 2. Roles Required
    decorated_roles = roles_required(["admin"])(mock_view)
    
    user_no_roles = MockUser(roles=["user"])
    req_no_roles = MockRequest(user=user_no_roles)
    with pytest.raises(Forbidden):
        await decorated_roles(request=req_no_roles)
    
    user_admin = MockUser(roles=["admin"])
    req_admin = MockRequest(user=user_admin)
    assert await decorated_roles(request=req_admin) == "OK"
    
    # Superuser bypass
    user_root = MockUser(is_superuser=True)
    req_root = MockRequest(user=user_root)
    assert await decorated_roles(request=req_root) == "OK"
