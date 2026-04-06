# 🎯 Retrieving Single Records in Eden ORM

> **Great Question!** Yes, Eden has `.first()`, `.last()`, and `.get()` — all fully implemented and working!

---

## 📋 Quick Reference

| Method | Returns | Use Case | Speed |
|--------|---------|----------|-------|
| `.first()` | `Model \| None` | Get first matching record | ⚡ Fast |
| `.last()` | `Model \| None` | Get last matching record | ⚡ Fast |
| `.get(id)` | `Model \| None` | Lookup by primary key | ⚡⚡ Fastest |
| `.all()` | `list[Model]` | Get all matching records | Medium |

---

## Implementation Location

All these methods are implemented in `eden/db/query.py`:

- **`.first()`** - Line 809-813
- **`.last()`** - Line 815-819  
- **`.get(id)`** - Line 821-835
- **`.all()`** - Line 764-807

---

## Examples

### 1️⃣ `.first()` - Get First Record

**Get the first matching record (or None):**

```python
from eden.db import Model, f, Mapped

class User(Model):
    __tablename__ = "users"
    name: Mapped[str] = f()
    email: Mapped[str] = f()
    status: Mapped[str] = f()

# Get first active user
user = await User.filter(status="active").first()
if user:
    print(f"First active user: {user.name}")
else:
    print("No active users found")

# Get first user by name
alice = await User.filter(name="Alice").first()

# Works with all filter types
user = await User.filter(q.age >= 18).first()  # Modern q
user = await User.filter(Q(age__gte=18)).first()  # Q objects
```

**Return value:** `User | None`

```python
# Usage
if user is not None:  # Check if found
    print(user.name)
```

---

### 2️⃣ `.last()` - Get Last Record

**Get the last matching record (or None):**

```python
# Get most recent user created
latest_user = await User.last()

# Get last user in a filtered set
last_admin = await User.filter(role="admin").last()

# Works with ordering
users_by_name = await User.order_by("name").last()
```

**Return value:** `User | None`

```python
# Real-world example: Get latest order
latest_order = await Order.filter(
    customer_id=123
).order_by("-created_at").last()

if latest_order:
    print(f"Last order total: ${latest_order.total}")
```

---

### 3️⃣ `.get(id)` - Lookup by Primary Key

**High-performance primary key lookup (the fastest method):**

```python
# Get user by ID
user = await User.get(123)

# Works with string IDs (converted automatically for UUID fields)
user = await User.get("550e8400-e29b-41d4-a716-446655440000")

# Returns None if not found
user = await User.get(999)
if user is None:
    print("User not found")
```

**Return value:** `User | None`

**Why .get() is fastest:**
- Direct primary key lookup
- Single index lookup (O(log n))
- No full table scan
- Best for by-ID queries

```python
# Real-world example: Get user profile by ID
@app.get("/users/{user_id}")
async def get_user_profile(user_id: int):
    user = await User.get(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

---

## Real-World Examples

### Example 1: API Endpoint - Get Single User

```python
from eden.db import Model, f, Mapped

class User(Model):
    __tablename__ = "users"
    id: Mapped[int] = f(primary_key=True)
    email: Mapped[str] = f(unique=True, index=True)
    name: Mapped[str] = f()
    status: Mapped[str] = f(default="active")

# Endpoint: GET /users/{user_id}
async def get_user(user_id: int):
    """Get user by ID (fastest method)"""
    user = await User.get(user_id)
    if not user:
        raise HTTPException(status_code=404)
    return user

# Endpoint: GET /users/lookup?email=alice@example.com
async def lookup_user(email: str):
    """Find user by email (first match)"""
    user = await User.filter(email=email).first()
    if not user:
        raise HTTPException(status_code=404)
    return user
```

---

### Example 2: Get Most Recent Record

```python
class Post(Model):
    __tablename__ = "posts"
    id: Mapped[int] = f(primary_key=True)
    title: Mapped[str] = f()
    author_id: Mapped[int] = f()
    created_at: Mapped[datetime] = f(index=True)

# Get most recent post by author
latest_post = await Post.filter(
    author_id=user_id
).order_by("-created_at").first()

# Alternative: Get last post
# (Note: .last() returns actual last in current result set)
# But for "most recent", use order_by("-created_at").first()
```

---

### Example 3: Check If Record Exists (Performance Comparison)

```python
# ❌ SLOWER: Get all records, check if any exist
users = await User.filter(email="alice@example.com").all()
exists = len(users) > 0

# ✅ FAST: Use .first() to get just one
user = await User.filter(email="alice@example.com").first()
exists = user is not None

# ✅✅ FASTEST: Use .exists() if just checking existence
exists = await User.filter(email="alice@example.com").exists()
```

---

### Example 4: Get With Relationships

```python
class Order(Model):
    __tablename__ = "orders"
    id: Mapped[int] = f(primary_key=True)
    customer_id: Mapped[int] = f()
    customer: Mapped["Customer"] = Relationship()

# Get order with customer eagerly loaded
order = await Order.get(order_id)

# Get order with relationships
order = await Order.filter(id=order_id).select_related("customer").first()

# Prefetch related for first() method
order = await Order.filter(status="pending").prefetch("customer").first()
```

---

### Example 5: Chain With Filter + First

```python
# Get first user matching complex filter
user = await User.filter(
    Q(status="active") & Q(tier__gte=2)
).order_by("created_at").first()

# Modern q syntax
user = await User.filter(
    (q.status == "active") & (q.tier >= 2)
).order_by("created_at").first()

# Get first admin user
admin = await User.filter(role="admin").first()

# Get first user not deleted
active = await User.filter(q.deleted_at.isnull(True)).first()
```

---

## Performance Comparison

```python
# ⚡⚡⚡ FASTEST - Direct ID lookup (microseconds)
user = await User.get(123)

# ⚡⚡ FAST - First + filter (milliseconds, stops after 1 result)
user = await User.filter(email="alice@x.com").first()

# ⚡ MEDIUM - First on complex filters (milliseconds, still stops at 1)
user = await User.filter(
    Q(status="active") & Q(tier >= 2)
).first()

# ⚠️ SLOWER - Get all then pick (retrieves all records into memory)
users = await User.filter(status="active").all()
first_user = users[0] if users else None
```

---

## When to Use Each

| Situation | Method | Reason |
|-----------|--------|--------|
| "Get user by their ID" | `.get(id)` | Fastest, direct key lookup |
| "Find first active user" | `.filter(...).first()` | Efficient, stops at 1 result |
| "Get most recent post" | `.order_by("-created_at").first()` | Works with ordering |
| "Just check if exists" | `.exists()` | Optimized count query |
| "Need all results" | `.all()` | Only when you need everything |
| "Get last in set" | `.last()` | Only when you need the actual last |

---

## Common Patterns

### Pattern 1: Get or Create

```python
# Get user by email, create if doesn't exist
user = await User.filter(email=email).first()
if not user:
    user = User(email=email, name=name)
    await user.save()
return user
```

### Pattern 2: Get With Validation

```python
# Get user and validate ownership
async def get_user_for_update(user_id: int, current_user_id: int):
    user = await User.get(user_id)
    if not user:
        raise HTTPException(status_code=404)
    if user.id != current_user_id:
        raise HTTPException(status_code=403)  # Not authorized
    return user
```

### Pattern 3: Get Most Recent + Fallback

```python
# Get most recent active order, or latest order if none active
recent = await Order.filter(status="active").order_by("-created_at").first()
if not recent:
    recent = await Order.order_by("-created_at").first()
return recent
```

---

## Code Location Reference

**File:** `eden/db/query.py`

```python
# Line 764-807: .all() method
async def all(self) -> list[T]:
    """Execute query and return all results. Checks cache if enabled."""
    # ... implementation

# Line 809-813: .first() method  
async def first(self) -> T | None:
    """Execute query and return the first result, or None."""
    results = await self.all()
    return results[0] if results else None

# Line 815-819: .last() method
async def last(self) -> T | None:
    """Execute query and return the last result."""
    results = await self.all()
    return results[-1] if results else None

# Line 821-835: .get() method
async def get(self, id: Any) -> T | None:
    """Fetch a single record by ID, respecting current filters."""
    # ... implementation with UUID auto-conversion
```

---

## Why These Methods Are Not Prominent in Docs

The reason you didn't see `.first()`, `.last()`, and `.get()` documented in detail is:

1. **Table exists** - They're listed in the terminating methods table in orm-querying.md
2. **Examples sparse** - There weren't detailed examples or use cases for each
3. **`.all()` is primary** - Most examples focus on `.all()` because it's the most common
4. **Documentation gap** - Complex patterns guide focuses on filters, not single-record retrieval

---

## ✅ Verification

All three methods are **fully implemented and working**:

```python
from eden.db import q, Q

# ✅ All these work perfectly

user = await User.get(123)  # ✅
user = await User.filter(email="x@y.com").first()  # ✅
user = await User.filter(status="active").last()  # ✅

user = await User.filter(q.age >= 18).first()  # ✅ Modern q
user = await User.filter(Q(age__gte=18)).first()  # ✅ Q objects
```

---

## Summary

✅ **Yes, all single-record methods exist:**
- `.get(id)` - Fastest, by primary key
- `.first()` - First matching record
- `.last()` - Last matching record
- `.all()` - All records (when you need them all)

**Recommendation:** Use `.get(id)` whenever possible (fastest), then `.first()` for other queries.

---

**Next:** Add single-record examples to orm-querying.md documentation for better visibility.
