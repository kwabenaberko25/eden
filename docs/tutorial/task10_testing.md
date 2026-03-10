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
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio
          
      - name: Execute Pytest
        run: pytest
```

---

## 🎉 Tutorial Complete!

You have successfully built, secured, and prepared an Eden application for the world. 

### What's Next?

1. Explore the **[API Docs](/docs)** for deep-dives into each module.
2. Join the **[Discord Community](https://discord.gg/eden-framework)**.
3. Check out the **[Cookbook](/cookbooks)** for advanced SaaS patterns.

🌿 **Grow your vision with Eden.**
