# Task 10: Test & Automate

**Goal**: Maintain code integrity and confidence by building a comprehensive automated test suite using **Pytest**.

---

## 🧪 Step 10.1: Unit Testing Models

Testing your database logic isolately ensures your data integrity remains constant as you evolve your app.

**File**: `tests/test_users.py`

```python
import pytest
from app.models import User

@pytest.mark.asyncio
async def test_user_lifecycle():
    # 1. Test Creation
    user = await User.create(name="Tester", email="test@eden.dev")
    assert user.id is not None
    
    # 2. Test Retrieval
    found = await User.get(email="test@eden.dev")
    assert found.name == "Tester"
    
    # 3. Cleanup
    await user.delete()
```

---

## 🛰️ Step 10.2: Integration Testing Routes

Use the `AsyncClient` from `httpx` to simulate real-world API requests against your application.

**File**: `tests/test_api.py`

```python
import pytest
from httpx import ASGITransport, AsyncClient
from app import app

@pytest.fixture
async def client():
    """Create a test client for the application."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

@pytest.mark.asyncio
async def test_index_route(client):
    response = await client.get("/")
    assert response.status_code == 200
    assert "Welcome" in response.json()["message"]
```

---

## 🔄 Step 10.3: Continuous Integration (CI)

Automate your tests on every push. GitHub Actions is the standard tool for Eden projects.

**File**: `.github/workflows/ci.yml`

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  run-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: 3.11
      
      - name: Install dependencies
        run: pip install -e . pytest pytest-asyncio pytest-cov
      
      - name: Run tests
        run: pytest --cov=app tests/
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## 🎯 Step 10.4: Testing Forms & Validation

Ensure your schema validation works correctly:

```python
import pytest
from app.schemas.user import UserCreateSchema

@pytest.mark.asyncio
async def test_user_schema_validation():
    """Test that schema validation catches invalid input."""
    
    # Valid data should pass
    valid_data = {
        "name": "John Doe",
        "email": "john@example.com",
        "age": 25
    }
    schema = UserCreateSchema(**valid_data)
    assert schema.name == "John Doe"
    
    # Invalid email should fail
    with pytest.raises(ValueError):
        UserCreateSchema(
            name="Jane",
            email="invalid-email",
            age=25
        )
    
    # Age too young should fail
    with pytest.raises(ValueError):
        UserCreateSchema(
            name="Young User",
            email="young@example.com",
            age=15  # Less than 18
        )
```

---

## 🔐 Step 10.5: Testing Security & Permissions

Verify that your security rules work as expected:

```python
import pytest
from httpx import AsyncClient
from app import create_app
from app.models import User

@pytest.fixture
async def admin_user():
    """Create an admin user for tests."""
    return await User.create(
        name="Admin",
        email="admin@test.dev",
        is_admin=True
    )

@pytest.fixture
async def regular_user():
    """Create a regular user for tests."""
    return await User.create(
        name="Regular",
        email="user@test.dev",
        is_admin=False
    )

@pytest.mark.asyncio
async def test_admin_only_route(client, admin_user, regular_user):
    """Test that admin-only routes are protected."""
    
    # Admin should access successfully
    response = await client.get("/admin/metrics", headers={
        "Authorization": f"Bearer {admin_user.token}"
    })
    assert response.status_code == 200
    
    # Regular user should be forbidden
    response = await client.get("/admin/metrics", headers={
        "Authorization": f"Bearer {regular_user.token}"
    })
    assert response.status_code == 403
    
    # Unauthenticated should redirect to login
    response = await client.get("/admin/metrics")
    assert response.status_code == 401
```

---

## 📊 Step 10.6: Testing Database Transactions

Ensure your complex business logic works atomically:

```python
import pytest
from sqlalchemy import event
from app.models import User, Post

@pytest.mark.asyncio
async def test_user_post_cascade_delete():
    """Test that deleting a user cascades to their posts."""
    
    # Create a user with posts
    user = await User.create(name="Blogger", email="blog@test.dev")
    await Post.create(user_id=user.id, title="Post 1", content="Content 1")
    await Post.create(user_id=user.id, title="Post 2", content="Content 2")
    
    # Verify posts exist
    post_count = await Post.filter(user_id=user.id).count()
    assert post_count == 2
    
    # Delete user
    await user.delete()
    
    # Verify posts are cascaded deleted
    post_count = await Post.filter(user_id=user.id).count()
    assert post_count == 0

@pytest.mark.asyncio
async def test_payment_transaction_rollback():
    """Test that a failed payment doesn't charge the user."""
    
    user = await User.create(name="Buyer", email="buyer@test.dev")
    initial_balance = user.balance  # 100.00
    
    try:
        async with db.transaction():
            # Deduct from balance
            user.balance -= 50
            await user.save()
            
            # Simulate payment processor failure
            raise Exception("Payment gateway down")
    except Exception:
        pass
    
    # Reload user to verify balance wasn't actually deducted
    user = await User.get(id=user.id)
    assert user.balance == initial_balance
```

---

## 🚨 Step 10.7: Edge Cases & Error Testing

Test error handling and edge cases:

```python
import pytest
from eden.exceptions import NotFound, Unauthorized

@pytest.mark.asyncio
async def test_get_nonexistent_user(client):
    """Test 404 handling for missing resources."""
    response = await client.get("/users/999999")
    assert response.status_code == 404
    assert "not found" in response.json()["error"].lower()

@pytest.mark.asyncio
async def test_form_submission_with_missing_fields():
    """Test that missing required fields are caught."""
    response = await client.post("/users/join", json={
        "name": "Incomplete User"
        # Missing email and age
    })
    assert response.status_code == 422  # Unprocessable Entity
    assert "email" in response.json()["detail"]

@pytest.mark.asyncio
async def test_concurrent_requests():
    """Test that multiple concurrent requests don't cause issues."""
    import asyncio
    
    tasks = [
        client.post("/users", json={
            "name": f"User {i}",
            "email": f"user{i}@test.dev"
        })
        for i in range(10)
    ]
    
    responses = await asyncio.gather(*tasks)
    
    # All should succeed
    for response in responses:
        assert response.status_code == 201
    
    # All users should be created
    user_count = await User.count()
    assert user_count >= 10
```

---

## 📈 Step 10.8: Test Coverage & Reporting

Measure how much of your code is tested:

```bash
# Run tests with coverage report
pytest --cov=app --cov-report=html tests/

# Generate report
# Coverage report is in htmlcov/index.html
```

Aim for **80%+ code coverage** on critical paths (models, authentication, payments).

**File**: `pytest.ini`

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
addopts = --cov=app --cov-report=term-missing --cov-fail-under=80
```

---

### Quest Complete! 🎉

You've built a production-ready Eden application with:
- ✅ Database models and relationships
- ✅ HTTP routes and validation
- ✅ Beautiful HTML templates
- ✅ Form handling and submission
- ✅ Security and RBAC
- ✅ SaaS features (payments, storage, analytics)
- ✅ Production deployment
- ✅ Automated testing

**Next Steps**:
- Explore the [Core Concepts](../guides/routing.md) for advanced patterns
- Join the [Eden Community](https://discord.gg/eden) for support
- Share your project and get feedback!



---

## 🎉 Tutorial Complete!

You have successfully built, secured, and prepared an Eden application for the world. 

### What's Next?

1. Explore the **[API Docs](../index.md)** for deep-dives into each module.
2. Join the **[Discord Community](https://discord.gg/eden-framework)**.
3. Check out the **[Advanced Guides](../guides/htmx.md)** for advanced SaaS patterns.

🌿 **Grow your vision with Eden.**
