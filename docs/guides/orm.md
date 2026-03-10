# Data Layer: The Eden ORM 🗄️

Eden features a zero-config, async-first ORM built on **SQLAlchemy 2.0**. It combines the power of raw SQL with the elegance of a Django-inspired API.

## Defining Models

Models are Python classes that inherit from `Model`. They typically use the `f()` helper for a "Zen" definition experience with automatic type inference.

```python
from sqlalchemy.orm import Mapped
from eden.db import Model, f

class User(Model):
    name: Mapped[str] = f(max_length=100)
    age: Mapped[int] = f(nullable=True)
    is_active: Mapped[bool] = f(default=True)
```

---

## The QuerySet API

Eden eliminates the need for manual session handling for standard operations.

### Reading Data

```python
# Get all active users
users = await User.filter(is_active=True)

# Get a single user by ID
user = await User.get(id=1)

# Get all users (returns a list)
all_users = await User.all()

# Count records
count = await User.filter(is_active=True).count()
```

### Writing Data

```python
# Create and save a new record
new_user = await User.create(name="Eden", age=25)

# Update an existing record
await new_user.update(age=26)

# Delete a record
await new_user.delete()
```

---

## Advanced Querying 🚀

For complex logic, Eden provides `Q` objects and `F` expressions.

### `Q` Objects (AND/OR Logic)

```python
from eden.db import Q

# Find users who are either active OR younger than 30
users = await User.filter(Q(is_active=True) | Q(age__lt=30))
```

### `F` Expressions (Field-level Ops)

```python
from eden.db import F

# Increment age for all users directly in the database
await User.all().update(age=F('age') + 1)
```

---

## Aggregations 📊

Perform data analysis directly on your QuerySets.

```python
from eden.db import Sum, Avg, Max

results = await User.all().aggregate(
    total_age=Sum('age'),
    average_age=Avg('age'),
    oldest=Max('age')
)
# Returns {'total_age': 1500, 'average_age': 35.5, 'oldest': 99}
```

---

---

## Lookups & Filters Reference

Eden supports Django-style lookups across all Relationship and Field types using the `double_underscore` syntax.

### Relationship Traversal

You can filter across relationships by joining them with `__`. Eden handles the SQL joins automatically.

```python
# Django-style traversal
tasks = await Task.filter(project__name__icontains="Eden")

# Explicit Dot-notation (SQLAlchemy style)
# Eden still manages the auto-join!
tasks = await Task.filter(Project.name == "Eden")
```

| Lookup | Description | SQL Counterpart | Example |
| :--- | :--- | :--- | :--- |
| `exact` / `iexact` | (Case-insensitive) Exact match. | `=` / `ILIKE` | `name__iexact="eden"` |
| `contains` / `icontains` | (Case-insensitive) Substring match. | `LIKE %...%` | `name__icontains="ed"` |
| `startswith` / `endswith` | Starts or ends with value. | `LIKE ...%` | `name__startswith="E"` |
| `gt` / `gte` | Greater than (or equal to). | `>` / `>=` | `age__gt=21` |
| `lt` / `lte` | Less than (or equal to). | `<` / `<=` | `age__lt=65` |
| `in` | Value exists in list. | `IN (...)` | `id__in=[1, 2, 3]` |
| `isnull` | Check if field is null. | `IS NULL` | `age__isnull=True` |
| `range` | Between two values. | `BETWEEN` | `age__range=(18, 30)` |

---

## Relationships 🔗

Define connections between your models with ease.

```python
from sqlalchemy.orm import Mapped
from eden.db import Model, f

class Organization(Model):
    name: Mapped[str] = f()

class Member(Model):
    name: Mapped[str] = f()
    
    # Relationship with automatic Foreign Key (one-liner)
    # This automatically creates member.organization_id
    organization: Mapped["Organization"] = f(back_populates="members")
```

---

## Multi-Tenancy 🏢

Eden handles data isolation automatically via the `TenantMixin`.

```python
from eden.tenancy import TenantMixin

class Task(Model, TenantMixin):
    title: Mapped[str] = f()

# Queries are automatically scoped to the current tenant in the request context
tasks = await Task.all() 
```

---

## The `Resource` Pattern 📦

For enterprise applications, use `Resource` instead of `Model`. It automatically adds `id`, `created_at`, `updated_at`, and `is_deleted` (soft-delete) fields.

```python
from eden.resources import Resource

class Invoice(Resource):
    number: Mapped[str] = f()

# Invoices will NEVER be deleted from the DB; Invoice.delete() will only mark it.
```

---

## Transactions ⚡

Group multiple operations into an atomic unit.

```python
from eden.db import transaction

async with transaction():
    user = await User.create(name="Atomic")
    await Profile.create(user_id=user.id, bio="Core bio")
# If any operation fails, both are rolled back automatically.
```

---

---

## Real-World Dashboard Aggregation 📊

The ORM's power shines when building complex reporting interfaces.

```python
from eden.db import Sum, Count, Avg, Q
from datetime import datetime, timedelta

async def get_sales_stats():
    last_30_days = datetime.now() - timedelta(days=30)
    
    # Complex chain: filter, group by, and aggregate in one pass
    stats = await Invoice.filter(
        Q(created_at__gte=last_30_days) & ~Q(status="draft")
    ).aggregate(
        total_revenue=Sum("amount"),
        active_customers=Count("customer_id", distinct=True),
        average_ticket=Avg("amount")
    )
    
    return stats
```

### Prefetching & Joins

Avoid N+1 problems by eagerly loading related data.

```python
# Fetches all members AND their organizations in a single optimized query
members = await Member.all().prefetch_related("organization")

for member in members:
    print(member.organization.name) # No extra DB call!
```

**Next Steps**: [Authentication & Security](auth.md)
