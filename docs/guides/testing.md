# 🧪 High-Speed Reliability & Testing

**Build bulletproof SaaS applications with Eden's integrated testing infrastructure. From sub-millisecond unit tests to complex multi-tenant integration scenarios, Eden ensures your code is production-ready before it leaves your machine.**

---

## 🧠 Conceptual Overview

Eden’s testing philosophy centers on **Speed** and **Isolation**. We provide an async-native `TestClient` and transactional database fixtures that ensure every test runs in a "clean room" environment—fast, deterministic, and repeatable.

### The Testing Pipeline

```mermaid
graph TD
    A["Pytest Runner"] --> B["Eden: conftest.py Setup"]
    B --> C["Fixture: Transactional DB"]
    C --> D["Eden: TestClient Initialization"]
    D -- "> E["Test: Request" -> App -> DB"]
    E --> F["Assertion: Status / JSON / Fragment"]
    F --> G["Fixture: DB Rollback"]
    G --> H["Test Suite: Next Test"]
```

---

## 🏗️ Environment Setup

Eden uses `pytest` as its core engine. A professional `conftest.py` is the foundation of a high-fidelity test suite.

```python
# conftest.py
import pytest
from eden.testing import TestClient, create_test_app
from app.main import app as my_app

@pytest.fixture
async def client():
    """Returns an authenticated, tenant-aware TestClient."""
    async with TestClient(my_app) as client:
        yield client

@pytest.fixture(autouse=True)
async def transactional_db():
    """Wraps every test in a transaction that rolls back automatically."""
    from eden.db import db
    async with db.transaction() as tx:
        yield
        await tx.rollback()
```

---

## 🚀 The Eden `TestClient`

The `TestClient` is an extended version of the Starlette client, specifically tuned for Eden’s unique features like Identity and Multi-Tenancy.

### 1. Identity & Context
Easily simulate authenticated users and staff members without manually managing tokens or cookies.

```python
@pytest.mark.asyncio
async def test_admin_profile(client):
    # Log in as a specific user identity
    client.login(email="admin@eden.sh", is_superuser=True)
    
    response = await client.get("/admin/profile")
    assert response.status_code == 200
    assert response.json()["is_superuser"] is True
```

### 2. Multi-Tenant Isolation
Testing tenant leaks is the most critical part of SaaS development. Eden makes this declarative.

```python
@pytest.mark.asyncio
async def test_tenant_leaks(client):
    # Setup two separate tenants
    tenant_a = await Tenant.create(name="Team A")
    tenant_b = await Tenant.create(name="Team B")
    
    # Context: User is viewing Tenant A
    client.set_tenant(tenant_a)
    
    # Try to access a resource belonging to Tenant B
    response = await client.get(f"/api/v1/projects/{tenant_b.id}")
    
    # Assert that the system 'fails-secure' with a 404/403
    assert response.status_code == 404
```

---

## 📋 High-Fidelity Assertions

Eden provides a suite of semantic assertions to reduce boilerplate checks.

### JSON & Error Responses
```python
@pytest.mark.asyncio
async def test_api_validation(client):
    response = await client.post("/api/users", json={"email": "invalid"})
    
    # Assert standard Eden error format
    client.assert_error_response(response, code="VALIDATION_ERROR", status_code=400)
    
    # Assert partial JSON content
    client.assert_json_contains(response, "field", "email")
```

### Form & Fragment Testing
When building reactive UIs with HTMX, you often need to verify that only a specific HTML fragment was returned.

```python
@pytest.mark.asyncio
async def test_htmx_search_fragment(client):
    # Request a specific fragment via HTMX headers
    response = await client.get("/search?q=eden", headers={"HX-Request": "true"})
    
    # Verify fragment vs full page
    assert "<ul>" in response.text
    assert "<html>" not in response.text
```

---

## ⚡ Elite Pattern: Mocking Background Tasks

Never hit external services or slow down your suite with real worker execution during unit tests. Use `mock_tasks` to verify queuing logic.

```python
from eden.tasks import mock_tasks

@pytest.mark.asyncio
async def test_registration_emails(client):
    async with mock_tasks() as tasks:
        await client.post("/register", data={"email": "tester@eden.io"})
        
        # Verify the background task was queued with correct args
        assert tasks.has_been_called("send_welcome_email")
        assert tasks.call_args("send_welcome_email")["email"] == "tester@eden.io"
```

---

## 📄 API Reference: Test Utilities

### `TestClient` Methods

| Method | Description |
| :--- | :--- |
| `login(email)` | Sets current user identity for all subsequent requests. |
| `set_tenant(tenant)` | Sets the `X-Tenant-ID` header for multi-tenant context. |
| `get_json(path)` | GET request that returns parsed JSON directly. |
| `assert_status` | Detailed assertion that includes response body on failure. |
| `assert_error_response`| Verifies the response matches Eden's standard error schema. |

---

## 💡 Best Practices

1.  **Transactional Integrity**: Always use the `autouse` transactional fixture. It ensures your sequence of tests never pollutes your local development database.
2.  **Mock External Points**: Always mock Stripe, SendGrid, or AWS calls. Testing should be possible even when you are offline.
3.  **Test the Negative**: Don't just test that a feature works; test that it *doesn't* work when identity or permissions are missing.
4.  **Coverage Guardrails**: Use `pytest-cov` to ensure your critical business logic (Payments, Multi-tenancy) has 100% coverage.

---

**Next Steps**: [Deployment & Scaling](deployment.md)
