# Testing 🧪

Eden provides built-in testing utilities that make it easy to test routes, models, and forms. This guide covers the complete testing workflow, from basic unit tests to complex integration scenarios.

---

## The Testing Environment

Eden uses `pytest` as its primary testing framework. We recommend using the following fixtures in your `conftest.py`.

### 1. The Async Test Client

```python
import pytest
from eden.testing import TestClient
from app.main import app

@pytest.fixture
async def client():
    async with TestClient(app) as client:
        yield client
```

### 2. Transactional Database Fixture

To keep tests fast and isolated, run each test inside a database transaction that rolls back at the end.

```python
from eden.db import db

@pytest.fixture(autouse=True)
async def transactional_db():
    async with db.transaction() as transaction:
        yield
        await transaction.rollback()
```

---

## Testing Routes & APIs

### Verifying JSON Responses

```python
@pytest.mark.asyncio
async def test_get_user_api(client):
    response = await client.get("/api/users/1")
    
    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "name": "Eden User",
        "email": "user@eden.framework"
    }
```

### Testing Redirects & Cookies

```python
@pytest.mark.asyncio
async def test_login_flow(client):
    # This logic runs after the user confirms on a separate screen
    response = await client.post("/auth/login", data={
        "email": "admin@test.com",
        "password": "password123"
    })
    
    # Check for redirect
    assert response.status_code == 302
    assert response.headers["Location"] == "/dashboard"
    
    # Verify session cookie was set
    assert "eden_session" in client.cookies
```

---

## 📋 Testing Forms & Validation

Verify that your `Schema` classes handle invalid data correctly and return appropriate error messages.

```python
from app.schemas import SignupSchema
from eden.testing import assert_form_error

@pytest.mark.asyncio
async def test_signup_validation(client):
    # Test missing email
    response = await client.post("/signup", data={"password": "password101"})
    assert response.status_code == 200 # Form re-renders
    assert_form_error(response, "email", "field required")

    # Test weak password
    response = await client.post("/signup", data={
        "email": "test@eden.org", 
        "password": "123"
    })
    assert_form_error(response, "password", "at least 8 characters")
```

## 🏢 Testing Multi-Tenancy

In SaaS apps, it's critical to verify that users cannot access data from other tenants.

```python
@pytest.mark.asyncio
async def test_tenant_isolation(client, other_tenant_data):
    # Log in as Tenant A
    await client.login("user@tenant-a.com")
    
    # Try to access Tenant B's data
    response = await client.get(f"/projects/{other_tenant_data.id}")
    
    # Assert isolation works
    assert response.status_code == 404 # Or 403
```

---

## Testing Directives & Fragments

Eden's `TestClient` allows you to assert that specific template fragments were rendered.

```python
@pytest.mark.asyncio
async def test_htmx_search(client):
    # Request a specific fragment
    response = await client.get("/search?q=eden", headers={"HX-Request": "true"})
    
    # Assert that only the 'results' fragment was rendered
    assert "<ul>" in response.text
    assert "<html>" not in response.text # Should not contain layout
    assert response.status_code == 200
```

---

## Testing Background Tasks

When testing background tasks, you can use the `TaskMock` to verify a task was queued without actually executing it.

```python
from eden.tasks import mock_tasks

@pytest.mark.asyncio
async def test_email_queuing(client):
    async with mock_tasks() as tasks:
        await client.post("/auth/register", data={"email": "new@user.com"})
        
        # Verify the 'send_welcome_email' task was triggered
        assert tasks.has_been_called("send_welcome_email")
        assert tasks.call_args("send_welcome_email")["email"] == "new@user.com"
```

---

## 🛠️ Running Tests

Eden projects use standard `pytest`. If `pytest` is not found in your path, run it through the Python module.

```bash
# Run all tests
python3 -m pytest

# Run with verbose output and tracebacks
python3 -m pytest -vv --tb=short

# Run a specific file
python3 -m pytest tests/test_auth.py
```

## Best Practices

1. **Clear Context**: Always use the `db_session` fixture to ensure you're querying the same database state as your app.
2. **Isolation**: Tests should never depend on each other. If `test_b` requires data from `test_a`, move that setup into a shared fixture.
3. **Mocks**: Mock external APIs (Stripe, Twilio) using `pytest-mock` to prevent tests from making real network calls.
4. **Coverage**: Run with `--cov` to identify untested areas of your business logic.

---

**Next Steps**: [Deployment Guide](deployment.md)
