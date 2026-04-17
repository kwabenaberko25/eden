"""
Test script to verify admin JWT authentication fix.
"""
import asyncio
import jwt
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch

async def test_get_user_from_jwt():
    """Test that _get_user_from_jwt can extract and verify JWT tokens."""
    from eden.admin.views import _get_user_from_jwt
    from eden.auth.models import User
    
    # Create a test secret key
    secret_key = "test-secret-key-12345"
    
    # Create a test JWT payload
    payload = {
        "sub": "123",
        "email": "admin@test.com",
        "is_staff": True,
        "is_superuser": True,
        "test": True  # Mark as test user so it doesn't try to fetch from DB
    }
    
    # Encode the token
    token = jwt.encode(
        {
            **payload,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        },
        secret_key,
        algorithm="HS256"
    )
    
    # Create a mock request with the Authorization header
    request = Mock()
    request.headers = {
        "Authorization": f"Bearer {token}"
    }
    request.state = Mock()
    request.app = Mock()
    request.app.state = Mock()
    request.app.state.db = None
    
    # Mock the config to return our test secret key
    with patch("eden.config.get_config") as mock_get_config:
        mock_config = Mock()
        mock_config.secret_key = secret_key
        mock_get_config.return_value = mock_config
        
        # Call the function
        user = await _get_user_from_jwt(request)
        
        # Verify the user was created
        assert user is not None, "User should not be None"
        assert user.id == "123", f"User ID should be '123', got {user.id}"
        assert user.email == "admin@test.com", f"Email should be 'admin@test.com', got {user.email}"
        assert user.is_staff is True
        assert user.is_superuser is True
    
    print("[PASS] test_get_user_from_jwt")


async def test_check_staff_with_jwt():
    """Test that _check_staff can authenticate via JWT."""
    from eden.admin.views import _check_staff
    from eden.exceptions import Forbidden
    
    # Create a test secret key
    secret_key = "test-secret-key-12345"
    
    # Create a test JWT payload
    payload = {
        "sub": "123",
        "email": "admin@test.com",
        "is_staff": True,
        "is_superuser": True,
        "test": True
    }
    
    # Encode the token
    token = jwt.encode(
        {
            **payload,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        },
        secret_key,
        algorithm="HS256"
    )
    
    # Create a mock request with the Authorization header
    request = Mock()
    request.headers = {
        "Authorization": f"Bearer {token}"
    }
    request.state = Mock()
    request.state.user = None  # No user in state, should fall back to JWT
    request.app = Mock()
    request.app.state = Mock()
    request.app.state.db = None
    
    # Mock the config to return our test secret key
    with patch("eden.config.get_config") as mock_get_config:
        mock_config = Mock()
        mock_config.secret_key = secret_key
        mock_get_config.return_value = mock_config
        
        # Call the function - should not raise
        await _check_staff(request)
        
        # Verify that the user was set in request.state
        assert request.state.user is not None, "User should be set in request.state"
        assert request.state.user.id == "123"
    
    print("[PASS] test_check_staff_with_jwt")


async def test_check_staff_permission_check():
    """Test that _check_staff rejects non-staff users."""
    from eden.admin.views import _check_staff
    from eden.exceptions import Forbidden
    
    # Create a test secret key
    secret_key = "test-secret-key-12345"
    
    # Create a test JWT payload WITHOUT staff/superuser privileges
    payload = {
        "sub": "456",
        "email": "user@test.com",
        "is_staff": False,
        "is_superuser": False,
        "test": True
    }
    
    # Encode the token
    token = jwt.encode(
        {
            **payload,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        },
        secret_key,
        algorithm="HS256"
    )
    
    # Create a mock request
    request = Mock()
    request.headers = {
        "Authorization": f"Bearer {token}"
    }
    request.state = Mock()
    request.state.user = None
    request.app = Mock()
    request.app.state = Mock()
    request.app.state.db = None
    
    # Mock the config
    with patch("eden.config.get_config") as mock_get_config:
        mock_config = Mock()
        mock_config.secret_key = secret_key
        mock_get_config.return_value = mock_config
        
        # Call the function - should raise Forbidden
        try:
            await _check_staff(request)
            assert False, "Should have raised Forbidden"
        except Forbidden as e:
            assert "Staff access required" in str(e)
    
    print("[PASS] test_check_staff_permission_check")


async def main():
    """Run all tests."""
    print("Running admin JWT authentication tests...")
    print()
    
    await test_get_user_from_jwt()
    await test_check_staff_with_jwt()
    await test_check_staff_permission_check()
    
    print()
    print("[PASS] All tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
