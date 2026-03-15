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

## 🔗 Step 3.4: Relationships & Foreign Keys

For complex applications, you'll need models that reference each other. Let's define a `Post` model that belongs to a `User`.

**File**: `app/models/post.py`

```python
from eden.db import Model, f
from sqlalchemy.orm import Mapped, relationship
from datetime import datetime

class Post(Model):
    """A blog post written by a user."""
    title: Mapped[str] = f(max_length=255)
    content: Mapped[str] = f()  # No length limit for text
    user_id: Mapped[int] = f(foreign_key="user.id", index=True)
    created_at: Mapped[datetime] = f(default=datetime.utcnow)
    
    # Relationship: fetch the author without an extra query
    user: Mapped["User"] = relationship("User", back_populates="posts")
```

**File**: `app/models/user.py` (Updated)

```python
from sqlalchemy.orm import Mapped, relationship

class User(Model):
    name: Mapped[str] = f(max_length=255)
    email: Mapped[str] = f(max_length=255, unique=True, index=True)
    is_active: Mapped[bool] = f(default=True)
    profile_data: Mapped[dict] = f(json=True, default={})
    
    # Reverse relationship: access a user's posts
    posts: Mapped[list["Post"]] = relationship("Post", back_populates="user")
```

**Update** `app/models/__init__.py`:
```python
from .user import User
from .post import Post
```

---

## 🎯 Step 3.5: Eager Loading & Performance

When fetching users with their posts, Eden can load them efficiently to avoid N+1 queries:

```python
async def get_user_with_posts(user_id: int):
    # ❌ BAD: Lazy loading - runs 1 + N queries
    user = await User.get(id=user_id)
    posts = await user.posts  # Extra query!
    
    # ✅ GOOD: Eager loading - single query with JOIN
    user = await User.select_related("posts").get(id=user_id)
    # user.posts is already loaded, no extra query
    
    return {
        "user": user.to_dict(),
        "posts": [p.to_dict() for p in user.posts]
    }
```

---

## 🔍 Step 3.6: Filtering & Bulk Operations

Eden makes querying intuitive and safe:

```python
# Filter by multiple conditions
recent_posts = await Post.filter(
    user_id=user_id,
    created_at__gte=datetime(2024, 1, 1)
).order_by("-created_at").all()

# Update multiple records at once
await User.filter(is_active=False).update(profile_data={"status": "archived"})

# Count matching records
active_user_count = await User.filter(is_active=True).count()

# Delete with conditions
await Post.filter(created_at__lt=datetime(2023, 1, 1)).delete()
```

---

## ⚠️ Step 3.7: Error Handling in CRUD Operations

Always handle cases where data doesn't exist:

```python
async def safe_get_user(user_id: int):
    try:
        user = await User.get(id=user_id)
        return {"success": True, "user": user.to_dict()}
    except User.DoesNotExist:
        return {"success": False, "error": "User not found"}
    except Exception as e:
        # Log unexpected errors
        print(f"Database error: {e}")
        return {"success": False, "error": "Internal server error"}

# In your route:
@user_router.get("/{user_id}")
async def get_user(user_id: int):
    result = await safe_get_user(user_id)
    if not result["success"]:
        return Response(
            {"error": result["error"]}, 
            status_code=status.HTTP_404_NOT_FOUND
        )
    return result["user"]
```

---

### **Next Task**: [Building Routes & Views](./task4_routing.md)
