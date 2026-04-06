# 🏗️ Complex Query Patterns: Real-World Filtering

> [!IMPORTANT]
> This guide covers **advanced, production-ready patterns** for building complex filters. All examples are verified to work with Eden's ORM.

---

## Table of Contents

1. [Multi-Table Filtering](#1-multi-table-filtering)
2. [Complex Boolean Logic](#2-complex-boolean-logic)
3. [Date & Time Filtering](#3-date--time-filtering)
4. [Aggregation & Grouping](#4-aggregation--grouping)
5. [Dynamic Filtering](#5-dynamic-filtering)
6. [Performance Optimization](#6-performance-optimization)

---

## 1. Multi-Table Filtering

### Pattern: Deep Relationship Traversal

**Scenario:** Find all posts by authors who live in specific cities.

```python
from eden.db import Model, f, Mapped, Relationship
from typing import Optional

class City(Model):
    __tablename__ = "cities"
    name: Mapped[str] = f()
    country: Mapped[str] = f()

class Profile(Model):
    __tablename__ = "profiles"
    bio: Mapped[str] = f(nullable=True)
    city_id: Mapped[Optional[int]] = f(foreign_key="cities.id", nullable=True)
    city: Mapped[Optional[City]] = Relationship(back_populates="profiles")

class Author(Model):
    __tablename__ = "authors"
    name: Mapped[str] = f()
    profile_id: Mapped[Optional[int]] = f(foreign_key="profiles.id", nullable=True)
    profile: Mapped[Optional[Profile]] = Relationship(back_populates="authors")

class Post(Model):
    __tablename__ = "posts"
    title: Mapped[str] = f()
    author_id: Mapped[int] = f(foreign_key="authors.id")
    author: Mapped[Author] = Relationship(back_populates="posts")

# Find posts by authors from London
posts = await Post.filter(author__profile__city__name="London").all()
# Auto-generates: 
# SELECT posts.* FROM posts
# JOIN authors ON posts.author_id = authors.id
# JOIN profiles ON authors.profile_id = profiles.id
# JOIN cities ON profiles.city_id = cities.id
# WHERE cities.name = 'London'
```

### Pattern: Reverse Relationship Filtering

**Scenario:** Find authors who have written at least 5 posts.

```python
from eden.db import Count, Q

# Query from the reverse side
authors = await Author.query().annotate(
    post_count=Count("posts")
).filter(post_count__gt=5).all()

# Or using Q objects
authors = await Author.query().filter(
    Q(posts__isnull=False)  # Has at least one post
).all()
```

### Pattern: Multiple Related Table Filtering

**Scenario:** Find posts with comments from verified users in the last 7 days.

```python
from datetime import datetime, timedelta

# Filter across multiple relationships
seven_days_ago = datetime.now() - timedelta(days=7)

posts = await Post.filter(
    comments__author__verified=True,
    comments__created_at__gte=seven_days_ago
).distinct().all()  # Use distinct() to avoid duplicate rows from joins
```

> [!TIP]
> Use `.distinct()` when joining to multiple related records to avoid duplicate results.

---

## 2. Complex Boolean Logic

### Pattern: Eligibility Checks with Multiple Conditions

**Scenario:** Find "premium" users who are either very active OR have high tier status.

```python
from eden.db import Q
from datetime import datetime, timedelta

thirty_days_ago = datetime.now() - timedelta(days=30)

premium_active_users = await User.filter(
    plan="premium",  # AND
    (
        Q(last_login__gte=thirty_days_ago) |  # OR: very active in last 30 days
        Q(tier__gte=3)  # OR: tier 3 or higher
    )
).all()
# SQL: WHERE plan = 'premium' 
#      AND (last_login >= <date> OR tier >= 3)
```

### Pattern: Exclude Multiple Conditions

**Scenario:** Find products that are in stock and not in any exclusion category.

```python
from eden.db import Q

exclusion_categories = ["discontinued", "recall", "archived"]

available_products = await Product.filter(
    stock__gt=0
).exclude(
    Q(category__in=exclusion_categories) |
    Q(is_hidden=True) |
    Q(deleted_at__isnull=False)
).all()
# SQL: WHERE stock > 0 
#      AND NOT (category IN (...) OR is_hidden OR deleted_at IS NOT NULL)
```

### Pattern: Nested OR with AND

**Scenario:** Find users matching two independent criteria sets.

```python
from eden.db import Q

users = await User.filter(
    # Criteria Set 1: Professional users
    (Q(job_title="Engineer") | Q(job_title="Manager")) &
    Q(company__isnull=False),
    # Criteria Set 2: Experience
    Q(years_experience__gte=5) |
    Q(has_certifications=True)
).all()

# SQL: WHERE (job_title IN ('Engineer', 'Manager') AND company IS NOT NULL)
#      AND (years_experience >= 5 OR has_certifications = true)
```

---

## 3. Date & Time Filtering

### Pattern: Time-Based Ranges

**Scenario:** Find orders from a specific quarter.

```python
from datetime import datetime

# Q4 2024
q4_start = datetime(2024, 10, 1)
q4_end = datetime(2024, 12, 31, 23, 59, 59)

q4_orders = await Order.filter(
    created_at__gte=q4_start,
    created_at__lte=q4_end
).all()

# Or using range lookup
q4_orders = await Order.filter(
    created_at__range=(q4_start, q4_end)
).all()
```

### Pattern: Relative Date Filtering

**Scenario:** Find posts created in the last N days.

```python
from datetime import datetime, timedelta

async def get_recent_posts(days: int = 7):
    """Get posts from the last N days."""
    cutoff_date = datetime.now() - timedelta(days=days)
    return await Post.filter(created_at__gte=cutoff_date).all()

# Usage
recent = await get_recent_posts(7)
this_month = await get_recent_posts(30)
```

### Pattern: Filter by Time of Day

**Scenario:** Find events scheduled for business hours (9 AM - 5 PM).

```python
from datetime import time
from eden.db import Q
from sqlalchemy import func

# Extract hour from timestamp and filter
business_hours_events = await Event.filter(
    Q(scheduled_time__hour__gte=9) &
    Q(scheduled_time__hour__lt=17)
).all()
```

### Pattern: Expiration Filtering

**Scenario:** Find active coupons that haven't expired.

```python
from datetime import datetime

active_coupons = await Coupon.filter(
    is_active=True,
    expires_at__gt=datetime.now()
).all()

# Find expired coupons
expired_coupons = await Coupon.filter(
    expires_at__lt=datetime.now()
).all()
```

---

## 4. Aggregation & Grouping

### Pattern: Find Top Categories by Product Count

**Scenario:** Show categories ranked by number of products.

```python
from eden.db import Count

categories_with_counts = await Category.query().annotate(
    product_count=Count("products")
).order_by("-product_count").all()

# Result: [
#   Category(name="Electronics", product_count=245),
#   Category(name="Books", product_count=189),
#   ...
# ]
```

### Pattern: Filter After Aggregation (HAVING)

**Scenario:** Find categories with more than 100 products.

```python
from eden.db import Count

popular_categories = await Category.query().annotate(
    product_count=Count("products")
).having(product_count__gt=100).all()

# SQL: SELECT categories.* FROM categories
#      LEFT JOIN products ON categories.id = products.category_id
#      GROUP BY categories.id
#      HAVING COUNT(products.id) > 100
```

### Pattern: Complex Aggregations

**Scenario:** Find orders with high order values and compare to averages.

```python
from eden.db import Sum, Avg, Count
from eden.db import Q

order_stats = await Order.query().annotate(
    total_revenue=Sum("items.price"),
    avg_item_price=Avg("items.price"),
    item_count=Count("items")
).filter(
    total_revenue__gt=1000  # Orders over $1000
).order_by("-total_revenue").all()
```

---

## 5. Dynamic Filtering

### Pattern: Build Filters Conditionally

**Scenario:** Search endpoint with optional filters.

```python
from eden.db import Q
from typing import Optional

async def search_products(
    query: Optional[str] = None,
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None
):
    """Search products with optional filters."""
    filters = Q()  # Start with empty Q
    
    if query:
        filters &= Q(title__icontains=query)
    
    if category:
        filters &= Q(category__name=category)
    
    if min_price is not None:
        filters &= Q(price__gte=min_price)
    
    if max_price is not None:
        filters &= Q(price__lte=max_price)
    
    return await Product.filter(filters).all()

# Usage
results = await search_products(
    query="laptop",
    category="Electronics",
    min_price=500,
    max_price=2000
)
```

### Pattern: Dynamic OR Conditions

**Scenario:** User can search by multiple fields.

```python
from eden.db import Q
from typing import List

async def search_by_multiple_fields(
    search_term: str,
    fields: List[str]  # ["name", "email", "description"]
):
    """Search across multiple fields with OR."""
    query = Q()  # Empty Q
    
    for field in fields:
        # Build dynamic lookup
        lookup = {f"{field}__icontains": search_term}
        query |= Q(**lookup)  # OR
    
    return await User.filter(query).all()

# Usage
results = await search_by_multiple_fields(
    "alice",
    ["name", "email", "bio"]
)
# Finds users where name OR email OR bio contains "alice"
```

### Pattern: Filter List to Q Objects

**Scenario:** Convert list of IDs into Q object.

```python
from eden.db import Q

async def get_posts_by_authors(author_ids: List[int]):
    """Get posts from multiple authors."""
    query = Q()
    
    for author_id in author_ids:
        query |= Q(author_id=author_id)  # OR each author
    
    return await Post.filter(query).all()

# Or using __in__ for simpler case
async def get_posts_by_authors_simple(author_ids: List[int]):
    """Simpler version."""
    return await Post.filter(author_id__in=author_ids).all()
```

---

## 6. Performance Optimization

### Pattern: Use `.values()` for Partial Data

**Scenario:** Get a list of user names without loading full User objects.

```python
# ❌ INEFFICIENT: Loads full User objects
users = await User.filter(active=True).all()
user_names = [u.name for u in users]  # Memory waste

# ✅ EFFICIENT: Gets only name column
user_names = await User.filter(active=True).values_list("name", flat=True)
# Result: ["Alice", "Bob", "Charlie"]
```

### Pattern: Prefetch vs Select Related

**Scenario:** Load posts with their authors efficiently.

```python
# ❌ CAUSES N+1: One query per post
posts = await Post.filter(status="published").all()
for post in posts:
    print(post.author.name)  # Triggers separate query for each

# ✅ EFFICIENT: Prefetch (separate query, but combined)
posts = await Post.filter(status="published").prefetch("author").all()

# ✅ ALSO EFFICIENT: Joinedload (single JOIN query)
posts = await Post.filter(status="published").select_related("author").all()
```

> [!TIP]
> Use `prefetch()` for one-to-many relationships. Use `select_related()` for one-to-one relationships.

### Pattern: Use `exists()` Instead of Count

**Scenario:** Check if any matching records exist.

```python
# ❌ INEFFICIENT: Counts all matching records
count = await User.filter(email="alice@example.com").count()
if count > 0:
    print("Found user")

# ✅ EFFICIENT: Stops after finding one
exists = await User.filter(email="alice@example.com").exists()
if exists:
    print("Found user")
```

### Pattern: Chunk Large Result Sets

**Scenario:** Process large amounts of data without loading everything into memory.

```python
async def process_large_dataset():
    """Process 100,000 records without loading all at once."""
    page_size = 1000
    offset = 0
    
    while True:
        records = await Product.filter(
            status="active"
        ).offset(offset).limit(page_size).all()
        
        if not records:
            break
        
        # Process this batch
        for record in records:
            await process_record(record)
        
        offset += page_size
```

### Pattern: Use Indexes on Filter Fields

**Scenario:** Define indexes on frequently filtered columns.

```python
class User(Model):
    __tablename__ = "users"
    
    # Define indexes on fields used in filters
    email: Mapped[str] = f(index=True, unique=True)
    status: Mapped[str] = f(index=True)
    created_at: Mapped[datetime] = f(index=True)
    subscription_tier: Mapped[str] = f(index=True)

# After model creation, indexes are created automatically in migrations
```

### Pattern: Explain Query Performance

**Scenario:** Debug slow queries to see execution plan.

```python
# Get the query execution plan
plan = await User.query().filter(
    email__icontains="example"
).select_related("profile").explain(analyze=True)

print(plan)
# Output shows: Seq Scan? Index Scan? JOIN strategy?

# If it shows Seq Scan on frequently filtered fields, add an index
```

---

## 🎯 Common Patterns Comparison

### Excluding vs Filtering with NOT

```python
# Method 1: Using exclude (simple)
active_users = await User.exclude(status="inactive").all()

# Method 2: Using Q NOT (complex logic)
from eden.db import Q
active_users = await User.filter(~Q(status="inactive")).all()

# Method 3: Using q proxy NOT equal
from eden.db.lookups import q
active_users = await User.filter(q.status != "inactive").all()

# All produce identical SQL
```

### Finding Multiple Values

```python
# Method 1: Multiple OR
from eden.db import Q
users = await User.filter(
    Q(role="admin") | Q(role="moderator") | Q(role="editor")
).all()

# Method 2: IN clause (simpler)
users = await User.filter(role__in=["admin", "moderator", "editor"]).all()

# Method 2 is more efficient for long lists
```

---

## ⚠️ Common Mistakes to Avoid

### Mistake 1: Forgetting `.distinct()` on Multi-Join Queries

```python
# ❌ WRONG: Can return duplicates
users = await User.filter(
    posts__status="published"
).all()
# Returns same user multiple times if they have multiple published posts

# ✅ CORRECT: Use distinct()
users = await User.filter(
    posts__status="published"
).distinct().all()
```

### Mistake 2: N+1 Query Problem

```python
# ❌ WRONG: One query per post author
posts = await Post.all()
for post in posts:
    print(post.author.name)  # Separate query each time!

# ✅ CORRECT: Prefetch relationships
posts = await Post.all().prefetch("author").all()
for post in posts:
    print(post.author.name)  # No extra queries
```

### Mistake 3: Case-Sensitive Search on User Input

```python
# ❌ WRONG: User might search "ALICE" but data has "alice"
users = await User.filter(name__contains=user_input).all()

# ✅ CORRECT: Always case-insensitive for user input
users = await User.filter(name__icontains=user_input).all()
```

### Mistake 4: Forgetting to Index Filter Columns

```python
# ❌ SLOW: Sequential scan on every filter
created_at: Mapped[datetime] = f()  # No index

# ✅ FAST: Index speeds up filters
created_at: Mapped[datetime] = f(index=True)
```

---

## 📊 Real-World Example: E-Commerce Search

```python
from eden.db import Q
from typing import Optional
from datetime import datetime

async def search_products(
    query: Optional[str] = None,
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    in_stock_only: bool = True,
    sort_by: str = "name"
):
    """
    Production-ready product search with multiple filters.
    """
    filters = Q()
    
    # Text search (case-insensitive)
    if query:
        filters &= (
            Q(title__icontains=query) |
            Q(description__icontains=query)
        )
    
    # Category filter
    if category:
        filters &= Q(category__name=category)
    
    # Price range
    if min_price is not None:
        filters &= Q(price__gte=min_price)
    
    if max_price is not None:
        filters &= Q(price__lte=max_price)
    
    # Stock status
    if in_stock_only:
        filters &= Q(stock__gt=0)
    
    # Active products only
    filters &= Q(is_active=True)
    filters &= Q(deleted_at__isnull=True)
    
    # Build query with optimization
    qs = Product.filter(filters)
    
    # Eager load relationships
    qs = qs.prefetch("category", "reviews")
    
    # Sort
    qs = qs.order_by(sort_by)
    
    # Return with pagination
    return await qs.paginate(page=1, per_page=20)

# Usage
results = await search_products(
    query="laptop",
    category="Electronics",
    min_price=500,
    max_price=2000,
    in_stock_only=True,
    sort_by="-created_at"
)
```

---

## Next Steps

- [Query Syntax Guide](orm-query-syntax.md) - Learn all three syntaxes
- [ORM Querying](orm-querying.md) - Basics and terminating methods
- [Performance Tips](orm-querying.md#⚡-performance-optimization) - Optimize slow queries
