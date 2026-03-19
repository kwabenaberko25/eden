# Project Structure 🏗️

**A professional Eden project follows a clean, modular layout designed to scale from a single experimental script to a multi-billion row enterprise SaaS.**

---

## 📂 The "Premium-Flat" Layout

When you run `eden new`, your project is initialized with a structure optimized for both clarity and industrial performance:

```mermaid
graph TD
    Root["/ (Project Root)"] --> App["app.py (Entry)"]
    Root --> Models["models.py (Data)"]
    Root --> Routes["routes/ (Logic)"]
    Root --> Templates["templates/ (Views)"]
    Root --> Static["static/ (Assets)"]
    Root --> Tests["tests/ (Quality)"]
    
    subgraph "The Core"
        App
        Models
    end
```

---

## 🏛️ Scalability Profiles

Choose the layout that matches your architectural complexity:

### 1. Minimal (Single File)

Ideal for microservices or lightweight proxies.

- **Files**: `app.py`
- **Logic**: All routes and models contained in one high-performance file.

### 2. Standard (Premium-Flat)

The default for 80% of applications.

- **Files**: `app.py`, `models.py`, `/routes`, `/templates`
- **Use Case**: Robust, standalone web applications with a clear separation of concerns.

### 3. Industrial (Domain-Driven)

For complex SaaS or multi-tenant applications.

- **Structure**: `app/core/`, `app/domain/`, `app/infra/`
- **Use Case**: Enterprise apps with complex business logic and heavy integration requirements.

---

## 🧩 Architectural Patterns

### Pattern: The Service Layer

For logic that spans multiple models or requires external integrations (e.g., Stripe, Email), use a **Service Layer**.

```python
# services/user_service.py
class UserService:
    @staticmethod
    async def create_premium_user(data: UserSchema):
        # 1. Create Model
        user = await User.create_from(data)
        # 2. Trigger Side Effects
        await app.task.kiq("send_welcome_email", user_id=user.id)
        return user
```

### Pattern: Modular Routing

As your API grows, decompose it into semantic routers.

```python
# routes/users.py
from eden import Router
user_router = Router(prefix="/users")

@user_router.get("/")
async def list_users(): ...

# In app.py
app.include_router(user_router)
```

---

## 🛡️ Core Configuration

Eden prioritizes environment-based configuration to ensure your code is portable across staging and production.

### `.env` (The Identity)

Your secrets and environment toggles. Eden automatically detects this file and populates the `app.config` namespace.

```text
DEBUG=True
DATABASE_URL=postgres://user:pass@localhost:5432/db
SECRET_KEY=y0ur-5ecr3t-k3y
```

### `settings.py` (The Manifest)

Use this file to define typed configuration classes for your application, pulling values from environment variables with safe defaults.

---

## 🧪 Testing Hierarchy

Organize your `tests/` directory to mirror your application logic:

```text
tests/
├── conftest.py       # Global fixtures & DB setup
├── test_models.py    # Unit tests for Data Layer
├── test_routes/      # Integration tests for APIs
└── test_services/    # Unit tests for Business Logic
```

---

### 🚀 Ready to Scale?

Explore the [Advanced Deployment Guide](../guides/deployment.md) or master the [ORM Relationships](../guides/orm.md).
