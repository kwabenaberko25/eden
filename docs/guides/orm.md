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
    avatar: Mapped[str] = f(upload_to="avatars") # File upload support

```

---

## The QuerySet API

Eden eliminates the need for manual session handling for standard operations.

### Reading Data

```python
# Get all active users
users = await User.filter(is_active=True)

# Get a single user by Primary Key
user = await User.get(1)

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

## 🏗️ Unified Schema Integration

Eden bridges the gap between your **Validation Layer** (Schemas/Forms) and your **Data Layer** (Models). This integration ensures that user input is safely and efficiently ingested into your database.

### 1. Creating from User Input (`create_from`)

The `create_from` class method allows you to take a validated schema or form and create a database record in one step. It is **security-aware**: it automatically filters out any fields present in the schema that are not defined on the model (e.g., a "confirm_password" field used only for UI validation).

```python
@app.post("/signup")
@app.validate(SignupSchema, template="signup.html")
async def signup(credentials: SignupSchema):
    # 'credentials' has confirmation fields and UI flags.
    # User.create_from pulls ONLY the fields that match the User model.
    user = await User.create_from(credentials)
    
    # You can still pass manual overrides
    # user = await User.create_from(credentials, is_admin=False)
    
    return redirect("/login")
```

### 2. Safeguarded Updates (`update_from`)

Similar to creation, `update_from` allows you to apply updates to an existing instance. This is ideal for profile edits or settings pages.

```python
@app.post("/profile/edit")
@app.validate(ProfileSchema, template="profile.html")
async def profile_update(request, credentials: ProfileSchema):
    user = await User.get(request.user.id)
    
    # Applies changes and saves to DB automatically.
    # Only fields with values in the schema are updated.
    await user.update_from(credentials)
    
    return redirect("/profile")
```

### 3. Smart Extraction (`to_schema`)

Every model can generate a **Schema** (Pydantic model) that carries over its constraints and **UI metadata** defined via the `f()` helper.

| Feature | Description |
| :--- | :--- |
| **Constraint Sync** | `max_length` and `nullable` constraints in SQL are mirrored in the Schema. |
| **Aesthetic Persistence** | Your `label`, `widget`, and `placeholder` settings follow the field. |
| **Lazy Generation** | Generate schemas on-the-fly for dynamic API responses or filters. |

```python
# Create a schema for a specific administrative view
AdminUserSchema = User.to_schema(exclude=["password_hash", "last_login"])

# Use it as a form for rendering an admin edit page
form = AdminUserSchema.as_form()
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

> **Important**: `TenantMixin` **MUST** come before `Model` in the inheritance list.

```python
from eden.tenancy import TenantMixin

# CORRECT: TenantMixin comes FIRST
class Task(TenantMixin, Model):
    title: Mapped[str] = f()

# Queries are automatically scoped to the current tenant in the request context
tasks = await Task.all() 
```

### Fail-Secure Behavior
If tenant context is missing, queries return zero results to prevent data leakage. See [Tenancy Guide](tenancy.md) for admin override details.

### Advanced Field Options

The `f()` helper supports advanced options for rapid development:

| Option | Description | Example |
| :--- | :--- | :--- |
| `json=True` | Stores data as a JSON blob. | `data: dict = f(json=True)` |
| `foreign_key` | Explicitly define a FK. | `user_id = f(foreign_key="users.id")` |
| `org_id=True` | Marks field as an Organization identifier. | `org = f(org_id=True)` |
| `choices` | Limits valid values. | `status = f(choices=["draft", "live"])` |

### Specialized Field Types

For more precision, Eden exports specialized field helpers:

```python
from eden.db import ManyToManyField, Reference, FileField

class Project(Model):
    # Reference is a one-liner for FK + Relationship
    owner: Mapped["User"] = Reference(back_populates="projects")
    
    # Many-to-Many with automatic association table inference
    members: Mapped[list["User"]] = ManyToManyField("User")
    
    # FileField for managed uploads
    logo: Mapped[str] = FileField(upload_to="logos")
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

### Database Sessions

For operations that require manual session management (like transactions), use the `db.session()` context manager.

```python
from eden.db import get_db

async def process_order(request):
    db = get_db(request)
    async with db.session() as session:
        # Pass session to model methods if needed, though most
        # Eden methods auto-detect the active session.
        order = await Order.create(status="paid")
        await Inventory.filter(product_id=1).update(stock=F("stock") - 1)
        # Session is committed automatically if no exception occurs.
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
