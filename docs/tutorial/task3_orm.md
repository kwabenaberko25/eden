# Task 3: Define Data Models (ORM)

**Goal**: Create database entities using Eden's fluent ORM and manage your data with ease.

---

## 💎 Step 3.1: Defining your first Model

Eden's ORM is built on **SQLAlchemy 2.0** but provides a much cleaner, more intuitive API inspired by modern Python features.

**File**: `app/models/user.py`

```python
from eden.db import Model, f
from sqlalchemy.orm import Mapped

class User(Model):
    """
    Core User entity for the application.
    """
    # Use f() for simple fields. Type hints are auto-mapped.
    name: Mapped[str] = f(max_length=255)
    email: Mapped[str] = f(max_length=255, unique=True, index=True)
    is_active: Mapped[bool] = f(default=True)
    
    # Complex metadata fields
    profile_data: Mapped[dict] = f(json=True, default={})
```

### Registering the Model

Ensure your model is exposed in the package:

**File**: `app/models/__init__.py`
```python
from .user import User
```

---

## ⚡ Step 3.2: Database Synchronization

In development (when using SQLite), Eden automatically synchronizes your schema on app startup.

1. Stop your server (`Ctrl+C`).
2. Verify `db.sqlite3` exists in your project root.
3. Restart with `eden run`. 
4. The `users` table is now live.

> [!IMPORTANT]
> For production (PostgreSQL/MySQL), use **Alembic** for controlled migrations:
> ```bash
> eden db migrate
> ```

---

## 🐍 Step 3.3: Interactive CRUD Mastery

Let's explore the power of the Eden ORM inside a Python script or shell.

```python
import asyncio
from app import create_app
from app.models import User

# Boot the app context
app = create_app()

async def demo_orm():
    # 1. CREATE: Instant persistence
    user = await User.create(
        name="Arturo", 
        email="arturo@eden.dev"
    )
    print(f"Created ID: {user.id}")

    # 2. READ: Multiple retrieval methods
    all_users = await User.all()
    target = await User.get(email="arturo@eden.dev")

    # 3. UPDATE: Atomic and efficient
    await target.update(name="Arturo V.")

    # 4. DELETE: Simple removal
    # await target.delete()

asyncio.run(demo_orm())
```

### Advanced Querying Preview
Eden supports chainable, readable filters:
```python
active_admins = await User.filter(is_active=True).order_by("-id").limit(10)
```

---

### **Next Task**: [Building Routes & Views](./task4_routing.md)
