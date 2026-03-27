import pytest
from unittest.mock import MagicMock, AsyncMock
from eden.auth.models import User
import asyncio

@pytest.mark.asyncio
async def test_createsuperuser_logic_fix():
    """
    Verifies that the User model can be instantiated with roles_json 
    and permissions_json (strings) without causing SQLAlchemy state errors.
    """
    # Mocking the database and session
    mock_session = AsyncMock()
    mock_db = MagicMock()
    mock_db.transaction.return_value.__aenter__.return_value = mock_session
    
    # Mock User.save to avoid actual DB calls but verify it's called
    original_save = User.save
    User.save = AsyncMock()
    
    try:
        # Simulate logic from eden/cli/auth.py
        email = "test@example.com"
        full_name = "Test User"
        password = "password123"
        
        # This was causing: TypeError: 'str' object has no attribute '_sa_instance_state'
        # when using 'roles=["admin"]' instead of 'roles_json=["admin"]'
        user = User(
            email=email,
            full_name=full_name,
            is_active=True,
            is_staff=True,
            is_superuser=True,
            roles_json=["admin"],
            permissions_json=["*"]
        )
        user.set_password(password)
        
        # Verify that accessing _sa_instance_state (which save() does) now works
        # because roles_json is just a JSON column, whereas roles was a relationship.
        from sqlalchemy.orm.attributes import instance_state
        state = instance_state(user)
        assert state is not None
        
        await user.save(mock_session)
        
        assert user.email == email
        assert user.is_superuser is True
        assert user.roles_json == ["admin"]
        assert user.permissions_json == ["*"]
        
        User.save.assert_called_once()
        
    finally:
        # Restore original save method
        User.save = original_save

if __name__ == "__main__":
    asyncio.run(test_createsuperuser_logic_fix())
