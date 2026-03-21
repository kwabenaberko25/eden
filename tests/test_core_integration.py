"""
Core Integration Tests for Eden Framework

Verifies the integrity of the application lifecycle, database isolation,
and testing infrastructure.
"""

import pytest
from eden.auth.models import User
from eden.testing import assert_status, TestUser

@pytest.mark.asyncio
async def test_app_initialization(test_app):
    """Verify that the test application initializes correctly with a database."""
    assert test_app.state.db is not None
    assert test_app.state.db._connected is True

@pytest.mark.asyncio
async def test_database_isolation_part_1(db_transaction):
    """Create a user in a transaction and verify it exists."""
    user = User(email="isolated@example.com", password_hash="hash")
    from eden.db.session import get_session
    session = get_session()
    session.add(user)
    await session.flush()
    
    # Verify it exists in this test
    exists = await User.query().filter(email="isolated@example.com").exists()
    assert exists is True

@pytest.mark.asyncio
async def test_database_isolation_part_2(db_transaction):
    """Verify that the user from part 1 was rolled back."""
    # This test should run after part 1
    # If isolation works, this user should NOT exist.
    exists = await User.query().filter(email="isolated@example.com").exists()
    assert exists is False

@pytest.mark.asyncio
async def test_client_request(client):
    """Verify that the Async TestClient can make requests."""
    # Eden has a default health check or similar? 
    # Let's try to hit a non-existent route to test 404
    response = await client.get("/_non_existent_route_")
    assert_status(response, 404)

@pytest.mark.asyncio
async def test_client_authentication(client):
    """Verify that client.set_user correctly injects authentication."""
    test_user = TestUser(id=99, email="auth-test@example.com")
    client.set_user(test_user)
    
    # Check headers
    assert "Authorization" in client.headers
    assert client.headers["Authorization"].startswith("Bearer ")
    
    # Verify token content if possible
    token = client.headers["Authorization"].split(" ")[1]
    import jwt
    from eden.config import get_config
    payload = jwt.decode(token, get_config().secret_key, algorithms=["HS256"])
    assert payload["sub"] == "99"
    assert payload["email"] == "auth-test@example.com"
