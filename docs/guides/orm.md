# Data Layer: The Eden ORM 🗄️

Eden features a zero-config, async-first ORM built on **SQLAlchemy 2.0**. It combines the power of raw SQL with the elegance of a Django-inspired API.

## Defining Models

Models are Python classes that inherit from `Model`. They typically use the `f()` helper for a "Zen" definition experience with automatic type inference.

```python
from eden import Model, f, Mapped

class User(Model):
    __reactive__ = True # Enabled Real-time sync for this model 🚀
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
# app.py
from eden import Eden

app = Eden(title="My App")

# The "Auto" Way: Simply set your database URL in state.
# Eden automatically initializes the ORM and manages connections.
app.state.database_url = "sqlite+aiosqlite:///database.db"

@app.on_startup
async def startup():
    # Eden handles connection; you just need to ensure tables exist
    from eden.db import get_db
    db = get_db()
    await db.create_all()
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

## Migrations

Database schema migrations are handled automatically with Alembic integration:

```python
# Generate migration from model changes
eden migrate create "Add user phone field"

# Apply pending migrations
eden migrate upgrade head

# Rollback last migration
eden migrate downgrade -1

# View migration history
eden migrate history
```

---

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

### One-to-Many Relationships

```python
from sqlalchemy.orm import Mapped, relationship
from typing import List
from eden.db import Model, f

# An organization has many projects
class Organization(Model):
    name: Mapped[str] = f(max_length=100)
    
    # One-to-many: organization -> projects
    projects: Mapped[List["Project"]] = relationship(back_populates="organization")

# A project belongs to an organization
class Project(Model):
    name: Mapped[str] = f(max_length=100)
    organization_id: Mapped[int] = f(foreign_key="organizations.id")
    
    # Many-to-one: project -> organization
    organization: Mapped["Organization"] = relationship(back_populates="projects")

# Usage
org = await Organization.get(1)
projects = await org.projects  # Async access to related data

# Or query through relationships
projects = await Project.filter(organization_id=1)
org_name = await projects[0].organization.name  # Single query with prefetch
```

### Many-to-Many Relationships

```python
from sqlalchemy import Table, Column, Integer, ForeignKey
from typing import List

# Association table for many-to-many
student_courses = Table(
    'student_courses',
    Base.metadata,
    Column('student_id', Integer, ForeignKey('students.id')),
    Column('course_id', Integer, ForeignKey('courses.id'))
)

class Student(Model):
    name: Mapped[str] = f()
    # Many-to-many: student -> courses
    courses: Mapped[List["Course"]] = relationship(
        "Course",
        secondary=student_courses,
        back_populates="students"
    )

class Course(Model):
    name: Mapped[str] = f()
    # Many-to-many: course -> students
    students: Mapped[List["Student"]] = relationship(
        "Student",
        secondary=student_courses,
        back_populates="courses"
    )

# Usage
student = await Student.get(1)
courses = await student.courses  # Get all courses for student

# Add relationship
await student.courses.append(course)

# Query through many-to-many
students_in_math = await Student.filter(courses__name="Advanced Math")
```

### Querying Through Relationships

```python
# Foreign key traversal (the Eden/Django way)
projects = await Project.filter(organization__name="Acme Corp")

# Reverse relationship traversal
orgs_with_active_projects = await Organization.filter(
    projects__status="active"
)

# Count related objects
org_project_counts = await Organization.all().annotate(
    project_count=Count("projects")
)
```

### Eager Loading (Avoiding N+1)

```python
# Bad: N+1 queries (1 fetch org + n fetches of projects)
orgs = await Organization.all()
for org in orgs:
    projects = await org.projects  # Extra query per iteration!

# Good: Single optimized query
orgs = await Organization.all().prefetch_related("projects")
for org in orgs:
    projects = org._cached_projects  # No extra queries
```

---

## Transactions & Atomicity

For multi-step operations that must succeed or fail together:

```python
from eden.db import get_db

# Simple transaction example
async def transfer_funds(from_user_id: int, to_user_id: int, amount: float):
    db = get_db()
    
    async with db.session() as session:
        # All operations below are atomic
        from_user = await User.get(from_user_id, session=session)
        to_user = await User.get(to_user_id, session=session)
        
        if from_user.balance < amount:
            raise ValueError("Insufficient funds")
        
from_user.balance -= amount
        to_user.balance += amount
        
        # Both saves commit together, or both rollback on error
        await from_user.save(session=session)
        await to_user.save(session=session)

# Complex transaction with savepoints
async def process_bulk_import(file_path: str):
    db = get_db()
    
    async with db.session() as session:
        for row in read_file(file_path):
            try:
                # Create savepoint for each record
                async with session.begin_nested():
                    user = await User.create(**parse_row(row), session=session)
                    await send_welcome_email(user)
            except Exception as e:
                # This record failed, but we continue with others
                logger.error(f"Failed to import row: {row}, error: {e}")
                continue
        
        # All successful records are committed
```

---

## Bulk Operations

For efficient batch processing:

```python
# Bulk create
users_data = [
    {"name": "Alice", "email": "alice@example.com"},
    {"name": "Bob", "email": "bob@example.com"},
    {"name": "Charlie", "email": "charlie@example.com"},
]

users = await User.bulk_create(users_data)

# Bulk update
await User.filter(is_active=False).delete()  # Soft delete

# Bulk insert with returning primary keys
users = await User.bulk_create(users_data, return_instances=True)
print([user.id for user in users])  # Get auto-generated IDs

# Update multiple records efficiently
await Product.filter(category="electronics").update(
    discount_percent=10
)
```

---

## Query Optimization Patterns

### Select Only Needed Fields

```python
# Avoid: loads entire model
users = await User.all()

# Better: only email for list view
class UserListSchema(Schema):
    id: int
    name: str
    email: str

users = await User.all().values("id", "name", "email")

# Or with a schema
users = await User.all().to_schema(UserListSchema)
```

### Pagination (Critical for Performance)

```python
# Avoid: cursor=0,limit=9999
# Better: offset-based
page = request.query_params.get("page", 1)
per_page = 20

users = await User.filter(is_active=True).order_by(
    "-created_at"
).limit(per_page).offset((page - 1) * per_page)

# For APIs, use cursor-based pagination
cursor = request.query_params.get("cursor")
if cursor:
    users = await User.filter(id__gt=cursor).limit(per_page)
else:
    users = await User.all().limit(per_page)

next_cursor = users[-1].id if len(users) == per_page else None
```

### Index-Aware Queries

```python
# Good: queries on indexed columns
class User(Model):
    email: Mapped[str] = f(unique=True, index=True)
    created_at: Mapped[datetime] = f(db_index=True)

# This query is fast (uses created_at index)
recent_users = await User.filter(
    created_at__gte=datetime.now() - timedelta(days=30)
)

# This query is slower (full table scan without index on is_active+status)
# Solution: create a composite index if this is a common query
class User(Model):
    __table_args__ = (
        Index('idx_active_status', 'is_active', 'status'),
    )
    is_active: Mapped[bool]
    status: Mapped[str]

active_premium = await User.filter(is_active=True, status="premium")
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

For complete tenant configuration, lifecycle management, billing integration, and multi-strategy setup, see [Tenant Configuration & Setup](tenant-configuration.md).

### Advanced Field Options

The `f()` helper supports advanced options for rapid development:

| Option | Description | Example |
| :--- | :--- | :--- |
| `json=True` | Stores data as a JSON blob. | `data: dict = f(json=True)` |
| `foreign_key` | Explicitly define a FK. | `user_id = f(foreign_key="users.id")` |
| `org_id=True` | Marks field as an Organization identifier. | `org = f(org_id=True)` |
| `choices` | Limits valid values. | `status = f(choices=["draft", "live"])` |

### AI-First: Vector Search

For builders of RAG, Semantic Search or AI apps, Eden provides native vector support.

```python
from eden.db.ai import VectorModel, VectorField

class Document(VectorModel):
    content: Mapped[str] = f()
    # 1536 is standard for OpenAI / Cohere embeddings
    embedding: Mapped[list[float]] = VectorField(dimensions=1536)

# Searching by meaning
results = await Document.semantic_search(query_vector, limit=5)
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

## Database Sessions

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
