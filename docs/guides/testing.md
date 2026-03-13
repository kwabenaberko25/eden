# Testing 🧪

Eden provides built-in testing utilities that make it easy to test routes, models, and forms. This guide covers the complete testing workflow.

## Setup

```python
import pytest
from eden.testing import TestClient

@pytest.fixture
async def client():
    """Create test client for your app."""
    from app import app
    return TestClient(app)

@pytest.fixture
async def db():
    """Provide clean database for each test."""
    await setup_test_db()
    yield
    await teardown_test_db()
```

## Testing Routes

```python
@pytest.mark.asyncio
async def test_get_user(client, db):
    """Test GET /users/{id}."""
    response = await client.get("/users/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1

@pytest.mark.asyncio
async def test_create_user(client, db):
    """Test POST /users."""
    response = await client.post(
        "/users",
        json={"name": "Alice", "email": "alice@test.com"}
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Alice"
```

## Testing Models

```python
@pytest.mark.asyncio
async def test_user_creation(db):
    """Test model creation."""
    user = await User.create(
        name="Bob",
        email="bob@test.com",
        password="securepassword"
    )
    
    assert user.id is not None
    assert user.name == "Bob"
    
    # Verify it's in database
    retrieved = await User.get(user.id)
    assert retrieved.email == "bob@test.com"

@pytest.mark.asyncio
async def test_query_filters(db):
    """Test ORM filtering."""
    await User.create(name="Admin", is_staff=True)
    await User.create(name="User", is_staff=False)
    
    admins = await User.filter(is_staff=True)
    assert len(admins) == 1
    assert admins[0].name == "Admin"
```

## Testing Forms

```python
@pytest.mark.asyncio
async def test_form_validation(client, db):
    """Test form validation."""
    response = await client.post(
        "/register",
        data={
            "email": "invalid-email",  # Invalid email
            "password": "short"  # Too short
        }
    )
    
    assert response.status_code == 400
    assert "email" in response.json()["errors"]
    assert "password" in response.json()["errors"]

@pytest.mark.asyncio
async def test_form_valid_submission(client, db):
    """Test valid form submission."""
    response = await client.post(
        "/register",
        data={
            "email": "user@example.com",
            "password": "securepassword123"
        }
    )
    
    assert response.status_code == 302  # Redirect on success
```

## Async Testing

Eden's test client handles async/await automatically:

```python
@pytest.mark.asyncio
async def test_async_flow(client, db):
    """Test async operations in routes."""
    # This will properly handle async code in your handlers
    response = await client.post("/async-endpoint")
    assert response.status_code == 200
```

## Mocking Dependencies

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_with_mock(client, db):
    """Mock external services."""
    with patch('app.email.send') as mock_send:
        mock_send.return_value = AsyncMock(return_value=True)
        
        response = await client.post("/send-email")
        
        assert response.status_code == 200
        mock_send.assert_called_once()
```
