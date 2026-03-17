# Querying & Lookups 🔍

Eden provides a powerful, Django-inspired QuerySet API that makes retrieving data intuitive and expressive.

## The QuerySet Interface

Every Eden model has a `.query()` method (or you can use the model class directly for shortcuts like `.filter()`) that returns a `QuerySet`. QuerySets are **lazy**: they don't hit the database until you iterate over them or call a terminating method.

### Terminating Methods

These methods trigger the execution of the SQL query:

- `.all()`: Returns a list of all matching records.
- `.first()`: Returns the first matching record or `None`.
- `.count()`: Returns the number of matching records as an integer.
- `.exists()`: Returns `True` if any records match the query.
- `.get(id)`: Fetches a single record by its primary key.

---

## Filtering Data

### Basic Filtering

Pass keyword arguments to match fields exactly.

```python
# Exact match
users = await User.filter(username="jdoe")

# Multiple conditions (AND)
active_admins = await User.filter(is_active=True, role="admin")
```

### Django-Style Lookups

Eden supports `field__lookup` syntax for advanced filtering.

| Lookup | Description | Example |
| :--- | :--- | :--- |
| `exact` | Exact match (case sensitive) | `name__exact="Eden"` |
| `iexact` | Case-insensitive exact match | `name__iexact="eden"` |
| `contains` | Substring match | `bio__contains="python"` |
| `icontains` | Case-insensitive substring match | `bio__icontains="PYTHON"` |
| `gt` / `gte` | Greater than (or equal to) | `age__gt=18` |
| `lt` / `lte` | Less than (or equal to) | `price__lte=100.0` |
| `in` | Match any in a list | `status__in=["draft", "published"]` |
| `isnull` | Check for NULL values | `deleted_at__isnull=True` |
| `range` | Between two values | `created_at__range=(start, end)` |

---

## Complex Logic with `Q` Objects

For `OR` queries or complex nested logic, use `Q` objects.

```python
from eden.db import Q

# OR Condition: Users named 'Alice' OR 'Bob'
users = await User.filter(Q(name="Alice") | Q(name="Bob"))

# Complex Nesting: (Active AND (Admin OR Staff))
query = Q(is_active=True) & (Q(role="admin") | Q(role="staff"))
users = await User.filter(query)
```

---

## Field-Level Operations with `F` Expressions

`F` expressions allow you to reference model fields directly in the query, performing calculations on the database side.

```python
from eden.db import F

# 1. Atomic Field-Level Updates
await Product.all().update(stock=F("stock") + 10)

# 2. Cross-Field Comparisons
# Find products where current stock is below safety threshold
danger_zone = await Product.filter(stock__lt=F("min_stock")).all()

# 3. Dynamic Field Math
expensive_items = await Product.filter(price__gt=F("cost") * 2).all()
```

---

## Aggregations & Annotations

### Aggregations

Calculate summaries across the entire QuerySet.

```python
from eden.db import Sum, Avg, Max

stats = await Order.filter(status="paid").aggregate(
    total_revenue=Sum("total_amount"),
    average_order=Avg("total_amount")
)
# Returns: {"total_revenue": 5000.50, "average_order": 125.00}
```

### Annotations

Add virtual fields to each record in the resulting list.

```python
from eden.db import Count

# Fetch authors and count their posts
authors = await Author.all().annotate(
    post_count=Count("posts"),
    premium_post_count=Count("posts", filter=Q(posts__is_premium=True))
).all()

print(authors[0].post_count) 
print(authors[0].premium_post_count)
```

---

## Advanced Query Optimization

### Partial Loading (`values`)

Load only specific columns to save memory and bandwidth.

```python
# Returns a list of dicts instead of model instances
emails = await User.all().values("id", "email")
```

### Pagination

Always paginate large datasets for performance.

```python
# Page 2 with 20 items per page
users = await User.all().limit(20).offset(20)

# Using the built-in .paginate helper
page = await User.all().paginate(page=2, per_page=20)
print(page.items, page.total, page.has_next)
```

---

## Grouping & Advanced Filtering (HAVING)

When performing aggregations, you often need to group results by a specific field or filter the results *after* the calculation has been performed (using `HAVING`).

### Grouping Results
Use `.group_by()` to segment your aggregations across categories.

```python
from eden.db import Sum, Count

# Get total sales and order count per category
category_stats = await Order.all() \
    .values("category") \
    .annotate(
        revenue=Sum("total_price"),
        orders=Count("id")
    ) \
    .group_by("category") \
    .all()

# Returns a list of dicts:
# [{"category": "Electronics", "revenue": 1500.0, "orders": 12}, ...]
```

### Filtering Aggregates with `HAVING`
The `.having()` method allows you to filter the results of your aggregations. This is essential for queries like "Categories with more than 10 orders".

```python
# Only get categories generating more than $1,000 in revenue
high_value_categories = await Order.all() \
    .values("category") \
    .annotate(revenue=Sum("total_price")) \
    .group_by("category") \
    .having(revenue__gt=1000) \
    .all()
```

### Advanced: Filtering Aggregates with Q

You can even use Q objects inside your `having` clauses for complex logic.

```python
# Categories with either huge revenue OR huge volume
trending = await Order.all() \
    .values("category") \
    .annotate(revenue=Sum("total_price"), volume=Count("id")) \
    .group_by("category") \
    .having(Q(revenue__gt=5000) | Q(volume__gt=100)) \
    .all()
```

---

## The Escape Hatch: Raw SQLAlchemy Integration

While Eden's ORM handles 95% of web development needs, sometimes you need the full specialized power of **SQLAlchemy** (e.g., Window Functions, Recursive CTEs, or complex Set operations like `UNION`).

### Using the `.statement` Property
Every `QuerySet` has a `.statement` property that returns the underlying SQLAlchemy `Select` object. You can modify this object using the standard SQLAlchemy API and then execute it using Eden's session.

```python
from sqlalchemy import func
from eden.db import get_session

# Example: Using a Window Function for a 'running total'
# 1. Build the base query in Eden
qs = Order.filter(status="paid").order_by("created_at")

# 2. Drop down to SQLAlchemy to add a Window Function
running_total = func.sum(Order.total_price).over(
    order_by=Order.created_at.asc()
).label("running_total")

# 3. Add the window column to the statement
stmt = qs.statement.add_columns(running_total)

# 4. Execute using Eden's session
db = await get_session()
results = await db.execute(stmt)

for row in results:
    # row is a SQLAlchemy Row object containing the Model instance and extra columns
    print(f"Order {row.Order.id}: Cumulative Revenue {row.running_total}")
```

---

**Next Steps**: [Authentication & Security](auth.md)
