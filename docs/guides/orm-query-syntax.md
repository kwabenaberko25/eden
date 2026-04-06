# 🔍 Query Syntax Guide: Three Ways to Filter in Eden

> [!TIP]
> **Eden provides THREE different query syntaxes** — all producing identical SQL, each suited to different preferences and use cases.

---

## 🎯 At a Glance: Syntax Comparison

| Goal | Django Style | Modern `q` | Q Objects |
|------|-------------|-----------|-----------|
| **Exact match** | `filter(age=30)` | `filter(q.age == 30)` | `filter(Q(age=30))` |
| **Greater than** | `filter(age__gt=30)` | `filter(q.age > 30)` | `filter(Q(age__gt=30))` |
| **Contains** | `filter(name__icontains="x")` | `filter(q.name.icontains("x"))` | `filter(Q(name__icontains="x"))` |
| **Multiple AND** | `filter(a=1, b=2)` | `filter(q.a == 1, q.b == 2)` | `filter(Q(a=1, b=2))` |
| **OR Logic** | ❌ Not possible | ❌ Not possible | `filter(Q(...) \| Q(...))` |
| **Complex Logic** | `.filter().filter()` | `.filter().filter()` | `filter((Q(...) \| Q(...)) & Q(...))` |
| **NOT** | `.exclude(field=x)` | `filter(q.field != x)` | `filter(~Q(field=x))` |

> [!IMPORTANT]
> All three syntaxes produce **identical SQL** and identical performance. Use whichever feels most natural to you.

---

## 1️⃣ Django-Style Lookups

The `field__lookup` syntax borrowed from Django ORM. Perfect if you're familiar with Django or prefer the `__` notation.

### Basic Usage

```python
from eden.db import Model, f, Mapped

class User(Model):
    __tablename__ = "users"
    name: Mapped[str] = f()
    age: Mapped[int] = f()
    email: Mapped[str] = f()
    status: Mapped[str] = f(default="active")

# Exact match (default)
users = await User.filter(status="active").all()

# Case-insensitive match
users = await User.filter(name__iexact="alice").all()

# Greater than
users = await User.filter(age__gt=30).all()

# Greater than or equal
users = await User.filter(age__gte=18).all()

# Less than
users = await User.filter(age__lt=65).all()

# Less than or equal
users = await User.filter(age__lte=65).all()
```

### String Lookups

```python
# Contains substring
products = await Product.filter(title__contains="laptop").all()

# Case-insensitive contains (⭐ recommended for user input)
products = await Product.filter(title__icontains="laptop").all()

# Starts with
users = await User.filter(email__startswith="alice").all()

# Case-insensitive starts with
users = await User.filter(email__istartswith="alice").all()

# Ends with
users = await User.filter(email__endswith="@gmail.com").all()

# Case-insensitive ends with
users = await User.filter(email__iendswith="@GMAIL.COM").all()
```

### Membership & Range Checks

```python
# IN clause
users = await User.filter(status__in=["active", "pending"]).all()

# BETWEEN range
orders = await Order.filter(amount__range=(100, 1000)).all()

# NULL checks
users = await User.filter(deleted_at__isnull=False).all()  # Not deleted
users = await User.filter(profile__isnull=True).all()      # No profile
```

### Multiple Conditions (AND)

```python
# All comma-separated conditions are AND
users = await User.filter(
    age__gte=18,
    status="active",
    name__icontains="alice"
).all()
# Result: age >= 18 AND status = 'active' AND name ILIKE '%alice%'

# Can chain .filter() calls (also AND)
users = await User.filter(age__gte=18).filter(status="active").all()
# Result: Same SQL
```

---

## 2️⃣ Modern `q` Proxy

The modern, Pythonic alternative using attribute access and standard Python operators.

> [!NOTE]
> The `q` proxy is **zero-boilerplate** and often preferred by modern Python developers. It provides attribute-based lookups instead of string concatenation with `__`.

### Basic Usage

```python
from eden.db.lookups import q

# Exact match
users = await User.filter(q.status == "active").all()

# Comparison operators
users = await User.filter(q.age > 30).all()
users = await User.filter(q.age >= 18).all()
users = await User.filter(q.age < 65).all()
users = await User.filter(q.age <= 65).all()
users = await User.filter(q.age != 30).all()
```

### String Methods

```python
from eden.db.lookups import q

# Case-insensitive contains (⭐ recommended for user input)
products = await Product.filter(q.title.icontains("laptop")).all()

# Case-sensitive contains
products = await Product.filter(q.title.contains("laptop")).all()

# Starts with
users = await User.filter(q.email.startswith("alice")).all()

# Case-insensitive starts with
users = await User.filter(q.email.istartswith("alice")).all()

# Ends with
users = await User.filter(q.email.endswith("@gmail.com")).all()

# Case-insensitive ends with
users = await User.filter(q.email.iendswith("@GMAIL.COM")).all()
```

### Membership & Range Checks

```python
from eden.db.lookups import q

# IN clause
users = await User.filter(q.status.in_(["active", "pending"])).all()

# BETWEEN range
orders = await Order.filter(q.amount.range(100, 1000)).all()

# NULL checks
users = await User.filter(q.deleted_at.isnull(False)).all()  # Not deleted
users = await User.filter(q.profile.isnull(True)).all()      # No profile
```

### Multiple Conditions (AND)

```python
from eden.db.lookups import q

# Multiple conditions in one call
users = await User.filter(
    q.age >= 18,
    q.status == "active",
    q.name.icontains("alice")
).all()
# Result: age >= 18 AND status = 'active' AND name ILIKE '%alice%'

# Can chain .filter() calls
users = await User.filter(q.age >= 18).filter(q.status == "active").all()
# Result: Same SQL
```

### Why Use `q`?

1. **Pythonic**: Uses standard operators (`>=`, `<=`, `!=`)
2. **IDE Support**: Better autocomplete and type hints
3. **Readable**: `q.age >= 30` is clearer than `age__gte=30`
4. **Modern**: Aligns with modern Python 3.10+ conventions
5. **Less String Magic**: No `__` concatenation to remember

---

## 3️⃣ Q Objects: Complex Boolean Logic

Use `Q` objects to handle OR, AND, and NOT operations for complex filtering logic.

> [!TIP]
> Q objects are essential when you need to express **OR conditions** or **complex nested boolean logic**.

### Basic Boolean Operations

```python
from eden.db import Q

# OR logic (at least one condition matches)
users = await User.filter(
    Q(role="admin") | Q(role="moderator")
).all()
# Result: role = 'admin' OR role = 'moderator'

# AND logic (all conditions must match)
users = await User.filter(
    Q(age__gte=18) & Q(status="active")
).all()
# Result: age >= 18 AND status = 'active'

# NOT logic (inverts the condition)
users = await User.filter(
    ~Q(status="banned")
).all()
# Result: NOT (status = 'banned')
```

### Complex Nested Logic

```python
from eden.db import Q

# (Admin OR Moderator) AND (Active OR Premium)
users = await User.filter(
    (Q(role="admin") | Q(role="moderator")) &
    (Q(status="active") | Q(plan="premium"))
).all()
# Result: (role = 'admin' OR role = 'moderator') 
#         AND (status = 'active' OR plan = 'premium')

# (New users) NOT (Banned users)
users = await User.filter(
    Q(created_at__gte=datetime.now() - timedelta(days=30)) &
    ~Q(banned=True)
).all()
# Result: created_at >= 30 days ago AND NOT (banned = true)
```

### Combining Q Objects with Regular Filters

```python
from eden.db import Q

# Mix Q objects with regular .filter() calls
users = await User.filter(
    Q(role="admin") | Q(role="moderator"),  # Q object
    status="active",                        # Regular filter (AND)
    age__gte=18                            # Regular filter (AND)
).all()
# Result: (role = 'admin' OR role = 'moderator')
#         AND status = 'active' 
#         AND age >= 18
```

### Using Q with Multiple Filters and Exclude

```python
from eden.db import Q

# Complex query with exclude
users = await User.filter(
    (Q(points__gte=1000) | Q(is_vip=True))
).exclude(
    Q(banned=True) | Q(deleted_at__isnull=False)
).all()
# Result: (points >= 1000 OR is_vip = true)
#         AND NOT (banned = true OR deleted_at IS NOT NULL)
```

---

## 📚 All Lookup Types Reference

### String Lookups

| Lookup | Django | `q` Method | Description |
|--------|--------|-----------|-------------|
| Exact | `name="alice"` | `q.name == "alice"` | Exact match (case-sensitive) |
| Case-insensitive exact | `name__iexact="alice"` | — | Case-insensitive exact match |
| Contains | `bio__contains="python"` | `q.bio.contains("python")` | Substring (case-sensitive) |
| **icontains** | `name__icontains="alice"` | `q.name.icontains("alice")` | **Case-insensitive substring ⭐** |
| Starts with | `email__startswith="a"` | `q.email.startswith("a")` | Prefix (case-sensitive) |
| Case-insensitive starts | `email__istartswith="a"` | `q.email.istartswith("a")` | Prefix (case-insensitive) |
| Ends with | `email__endswith=".com"` | `q.email.endswith(".com")` | Suffix (case-sensitive) |
| Case-insensitive ends | `email__iendswith=".COM"` | `q.email.iendswith(".COM")` | Suffix (case-insensitive) |

### Numeric/Comparison Lookups

| Lookup | Django | `q` Method | Description |
|--------|--------|-----------|-------------|
| Greater than | `age__gt=30` | `q.age > 30` | `>` |
| Greater or equal | `age__gte=30` | `q.age >= 30` | `>=` |
| Less than | `age__lt=30` | `q.age < 30` | `<` |
| Less or equal | `age__lte=30` | `q.age <= 30` | `<=` |
| Not equal | — | `q.age != 30` | `!=` |
| Exact | `age=30` | `q.age == 30` | `==` |

### Special Lookups

| Lookup | Django | `q` Method | Description |
|--------|--------|-----------|-------------|
| IN clause | `status__in=["a","b"]` | `q.status.in_(["a","b"])` | Value in list |
| BETWEEN | `age__range=(18,65)` | `q.age.range(18, 65)` | Between two values |
| IS NULL | `deleted__isnull=True` | `q.deleted.isnull(True)` | Null check |
| IS NOT NULL | `deleted__isnull=False` | `q.deleted.isnull(False)` | Not null |

---

## 🔗 Relationship Filtering: Multi-Table Queries

Eden automatically joins tables when you filter on related models.

### Automatic Relationship Joining

```python
from eden.db import Model, f, Mapped, Relationship

class Author(Model):
    __tablename__ = "authors"
    name: Mapped[str] = f()

class Post(Model):
    __tablename__ = "posts"
    title: Mapped[str] = f()
    author_id: Mapped[int] = f(foreign_key="authors.id")
    author: Mapped[Author] = Relationship(back_populates="posts")

# Filter by author's name (Eden auto-joins!)
posts = await Post.filter(author__name="Alice").all()
# Generated SQL: SELECT posts.* FROM posts 
#                JOIN authors ON posts.author_id = authors.id
#                WHERE authors.name = 'Alice'

# Using q proxy
from eden.db.lookups import q
posts = await Post.filter(q.author.name == "Alice").all()
# Same SQL as above

# Using Q objects
from eden.db import Q
posts = await Post.filter(Q(author__name="Alice")).all()
# Same SQL as above
```

### Deep Multi-Table Relationships

```python
class Author(Model):
    __tablename__ = "authors"
    name: Mapped[str] = f()

class Profile(Model):
    __tablename__ = "profiles"
    city: Mapped[str] = f()
    author_id: Mapped[int] = f(foreign_key="authors.id")
    author: Mapped[Author] = Relationship(back_populates="profile")

class Post(Model):
    __tablename__ = "posts"
    title: Mapped[str] = f()
    author_id: Mapped[int] = f(foreign_key="authors.id")
    author: Mapped[Author] = Relationship(back_populates="posts")

# Three levels deep! Eden auto-joins all relationships
posts = await Post.filter(author__profile__city="London").all()
# Generated SQL: SELECT posts.* FROM posts
#                JOIN authors ON posts.author_id = authors.id
#                JOIN profiles ON authors.id = profiles.author_id
#                WHERE profiles.city = 'London'
```

---

## ⚡ Practical Examples: Real-World Patterns

### Pattern 1: User Search with Multiple Filters

```python
from eden.db.lookups import q

async def search_users(name_query: str, min_age: int, max_age: int):
    """Search users by name and age range."""
    return await User.filter(
        q.name.icontains(name_query),  # Case-insensitive name search
        q.age >= min_age,               # Minimum age
        q.age <= max_age                # Maximum age
    ).order_by("name").all()

# Usage
users = await search_users("alice", 18, 65)
```

### Pattern 2: Filter by Status with OR Logic

```python
from eden.db import Q

async def get_publishable_posts():
    """Get posts that are published OR scheduled."""
    return await Post.filter(
        Q(status="published") | Q(status="scheduled")
    ).all()

# Usage
posts = await get_publishable_posts()
```

### Pattern 3: Exclude Soft-Deleted Records

```python
from datetime import datetime
from eden.db import Q

async def get_active_articles():
    """Get articles that haven't been soft-deleted."""
    return await Article.filter(
        ~Q(deleted_at__isnull=False)  # NOT soft-deleted
    ).all()

# Simpler with q:
from eden.db.lookups import q

async def get_active_articles():
    """Get articles that haven't been soft-deleted."""
    return await Article.filter(
        q.deleted_at.isnull(True)  # deleted_at IS NULL
    ).all()
```

### Pattern 4: Complex Eligibility Check

```python
from eden.db import Q
from datetime import datetime, timedelta

async def get_eligible_users_for_trial():
    """
    Find users who are eligible for trial:
    - Newly created (< 30 days)
    - Active OR Premium members
    - NOT already in trial
    """
    thirty_days_ago = datetime.now() - timedelta(days=30)
    
    return await User.filter(
        Q(created_at__gte=thirty_days_ago),  # New users
        (Q(status="active") | Q(plan="premium")),  # Active or premium
        ~Q(trial_started=True)  # Not already in trial
    ).all()
```

### Pattern 5: Filter with Prefetching Related Data

```python
async def get_posts_with_comments():
    """Get posts and eagerly load all their comments."""
    return await Post.filter(
        status="published"
    ).prefetch("comments").order_by("-created_at").all()

# Now access comments without N+1 queries
for post in posts:
    print(f"{post.title}: {len(post.comments)} comments")
```

---

## 🛡️ Security & Best Practices

### 1. Always Use Case-Insensitive for User Input

```python
# ❌ DON'T: Case-sensitive
users = await User.filter(email__contains=user_input).all()

# ✅ DO: Case-insensitive
users = await User.filter(email__icontains=user_input).all()
```

### 2. SQL Injection is Impossible

All three syntaxes use **parameterized queries** automatically:

```python
# ❌ This is SAFE (not vulnerable)
# Even malicious input is bound as a literal string
user_input = "' OR '1'='1"
users = await User.filter(name__icontains=user_input).all()
# SQL: WHERE name ILIKE '%<bind>'  (user_input is safely bound)

# ✅ Q objects are also safe
q = Q(username=user_input)  # Safe from injection
users = await User.filter(q).all()
```

### 3. Use F Expressions for Atomic Updates

```python
from eden.db import F

# ❌ DON'T: Race condition possible
user = await User.get(id=1)
user.points += 10
await user.save()

# ✅ DO: Atomic database-level update
await User.filter(id=1).update(points=F("points") + 10)
```

### 4. Index Your Filter Fields

```python
class User(Model):
    __tablename__ = "users"
    
    # Add index=True for frequently filtered fields
    email: Mapped[str] = f(unique=True, index=True)
    status: Mapped[str] = f(index=True)
    created_at: Mapped[datetime] = f(index=True)
```

---

## 📊 When to Use Each Syntax

### Use Django-Style When...
- ✅ You're coming from Django
- ✅ You prefer the `__` notation  
- ✅ Mixing with legacy Django code
- ✅ You want to keep similarity with Django

### Use Modern `q` When...
- ✅ You prefer Python operators
- ✅ Writing modern Python 3.10+
- ✅ You like attribute-based access
- ✅ IDE autocomplete matters to you
- ✅ You want to minimize string-based lookups

### Use Q Objects When...
- ✅ You need OR logic
- ✅ You need complex boolean combinations
- ✅ You're building filters dynamically
- ✅ Readability of complex logic matters

---

## 🔄 Migration Guide

### From Django-Style to Modern `q`

```python
# Before
users = await User.filter(
    age__gte=18,
    name__icontains="alice",
    status__in=["active", "pending"]
).all()

# After
from eden.db.lookups import q
users = await User.filter(
    q.age >= 18,
    q.name.icontains("alice"),
    q.status.in_(["active", "pending"])
).all()
```

### From Django-Style to Q Objects

```python
# Before (can't express OR with Django style)
users = await User.filter(role__in=["admin", "moderator"]).all()

# After (with Q objects)
from eden.db import Q
users = await User.filter(
    Q(role="admin") | Q(role="moderator")
).all()
```

---

## 💡 Key Takeaways

1. ✅ **All three syntaxes produce identical SQL** — performance is the same
2. ✅ **Choose based on preference** — use what feels most natural
3. ✅ **Mix and match** — you can use all three in the same codebase
4. ✅ **Q objects are essential** for OR and complex logic
5. ✅ **Always use case-insensitive** (`icontains`) for user input
6. ✅ **Eden auto-joins relationships** — just use `related__field` syntax
7. ✅ **SQL injection is impossible** — all syntaxes use parameterized queries

---

## 📖 Next Steps

- Read [Aggregations & Annotations](orm-querying.md#📈-aggregations--annotations) for summary queries
- Read [Performance Optimization](orm-querying.md#⚡-performance-optimization) to avoid N+1 problems
- Explore [Complex Patterns](orm-complex-patterns.md) for advanced use cases
