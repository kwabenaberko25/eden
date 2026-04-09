# Eden Database & ORM Architecture Guide

## Overview

Eden's database layer is built on **SQLAlchemy 2.0 Async** with a custom ORM that provides:
- **Active Record Pattern**: `Model.create()`, `model.save()`, `Model.query()`
- **Row-Level Security (RBAC)**: Integrated access control via `QuerySet._apply_rbac()`
- **Lifecycle Hooks**: Pre/post signals for `save`, `delete`, `create`
- **Async-First Design**: All I/O is non-blocking via asyncio
- **Multi-Tenancy**: Automatic schema isolation per tenant

## Core Components

### 1. Model (eden/db/base.py)

The base class for all database entities. Combines five mixins:

```python
class Model(Base, AccessControl, ValidatorMixin, LifecycleMixin, SerializationMixin, CrudMixin):
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, onupdate=get_utc_now)
```

**Key Points:**
- All models get a UUID primary key by default
- Timestamps are UTC-based naive datetimes (no tzinfo)
- Subclasses auto-generate table names from class name (e.g., `User` → `users`)
- Tenancy is auto-detected: any model with `tenant_id` is registered with the tenancy system

**Usage:**
```python
from eden.db import Model, StringField, ForeignKeyField

class User(Model):
    email: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    
    # Optional: Explicitly set table name
    __tablename__ = "custom_users"
```

### 2. Database (eden/db/session.py)

Manages connection pooling, session factory, and transaction contexts.

```python
db = Database("postgresql+asyncpg://user:pass@localhost/eden")
await db.connect(create_tables=True)

# Use in request context (middleware binds this)
Model._bind_db(db)  # Enables Model.query() to auto-acquire sessions
```

**Key Methods:**
- `connect(create_tables=bool)` - Initialize connection and optionally create tables
- `session()` - Async context manager for manual session control
- `transaction(session=None, commit=bool)` - Transaction context manager
- `savepoint(name=str)` - Create a savepoint within a transaction
- `set_schema(session, schema_name)` - PostgreSQL schema isolation (multi-tenancy)

**Session Resolution Strategy** (in priority order):
1. Explicit session passed to QuerySet
2. Async context variable (request-scoped session from middleware)
3. Global Model._db binding (from `db.connect()`)
4. Error or temporary session (depending on `config.db_strict_session_mode`)

### 3. QuerySet (eden/db/query.py)

Fluent query builder with lazy evaluation.

```python
# Basic queries
users = await User.query().filter(active=True).all()
user = await User.query().filter(email="alice@example.com").first()

# With relationships
posts = await User.query().selectinload("posts").filter(active=True).all()

# RBAC-aware
# (automatically filters based on current user's permissions)
visible_posts = await Post.query().all()  # Only shows readable posts

# Pagination
page = await User.query().paginate(page=1, per_page=20)

# Aggregation
total = await User.query().count()
avg_age = await User.query().aggregate(Avg("age"))

# Explicit RBAC for different actions
user_post = await Post.query().for_user(current_user, action="read").first()
```

**Key Features:**
- **Chainable**: `query().filter().selectinload().order_by().limit()`
- **Lazy**: Executes only when `.all()`, `.first()`, `.count()`, etc. are called
- **RBAC-Integrated**: `_apply_rbac()` automatically filters based on model `__rbac__` rules
- **Pagination**: Built-in `.paginate()` method returns `Page[T]` object

### 4. Lifecycle Hooks (Signals)

Eden provides pre/post hooks for model operations:

```python
from eden.db.signals import pre_save, post_save, pre_delete, post_delete

@pre_save.connect
async def before_save(sender, instance, is_new, session):
    # Runs before save (new or update)
    if is_new:
        print(f"Creating new {sender.__name__}")
    else:
        print(f"Updating {sender.__name__}")

@post_save.connect
async def after_save(sender, instance, is_new, session):
    # Runs after successful save
    if is_new:
        await send_welcome_email(instance)
```

**Available Signals:**
- `pre_save(sender, instance, is_new, session)` - Before save (create/update)
- `post_save(sender, instance, is_new, session)` - After save
- `pre_delete(sender, instance, session)` - Before delete
- `post_delete(sender, instance, session)` - After delete

### 5. Access Control (RBAC)

Row-level security via the `__rbac__` dictionary:

```python
from eden.db.access import AllowOwner, AllowRoles, AllowAuthenticated

class Post(Model):
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    user_id: Mapped[uuid.UUID]
    
    # Define RBAC rules per action
    __rbac__ = {
        "read": AllowAuthenticated(),     # Any logged-in user can read
        "create": AllowAuthenticated(),   # Any logged-in user can create
        "update": AllowOwner("user_id"),  # Only owner can update
        "delete": AllowOwner("user_id"),  # Only owner can delete
    }
```

**Built-in Rules:**
- `AllowPublic()` - Everyone, including unauthenticated
- `AllowAuthenticated()` - Any logged-in user
- `AllowOwner(field="user_id")` - Only the owner (checks field against user.id)
- `AllowRoles("admin", "moderator")` - Users with specific roles

**Custom Rules:**
```python
class AllowManagers(PermissionRule):
    def resolve(self, model_cls, user):
        return user and user.department_id == model_cls.department_id
    
    def check_instance(self, instance, user):
        return user and instance.department_id == user.department_id
```

## Common Patterns

### Creating Records

```python
# Method 1: .create() (recommended - includes validation & signals)
user = await User.create(email="alice@example.com", name="Alice")

# Method 2: .save() (also runs signals & validation)
user = User(email="bob@example.com", name="Bob")
await user.save()

# Method 3: Explicit session (for transactions)
async with db.transaction() as session:
    user = User(email="charlie@example.com", name="Charlie")
    await user.save(session=session)
```

### Updating Records

```python
# Load and modify
user = await User.get(id=user_id)
user.name = "Updated Name"
await user.save()

# Or use QuerySet.update()
await User.query().filter(active=False).update(archived=True)
```

### Deleting Records

```python
# Delete single instance
user = await User.get(id=user_id)
await user.delete()

# Delete via QuerySet
await User.query().filter(inactive_since="2020-01-01").delete()

# Soft delete (if model uses SoftDeleteMixin)
# Doesn't actually delete, just marks as deleted
await user.delete()  # Sets deleted_at timestamp
await User.query(include_deleted=True).all()  # See soft-deleted records
```

### Transactions

```python
# Best practice: Use db.transaction() context manager
async with db.transaction() as session:
    user = await User.create(email="alice@example.com", session=session)
    profile = await Profile.create(user_id=user.id, session=session)
    # Auto-commits on success, rolls back on exception

# Manual commit control
async with db.transaction(commit=False) as session:
    user = await User.create(email="alice@example.com", session=session)
    if validation_fails(user):
        # Session rolls back automatically since commit=False
        return error
    await session.commit()  # Explicit commit

# Savepoints (nested transactions)
async with db.transaction() as session:
    await User.create(email="alice@example.com", session=session)
    
    try:
        async with db.savepoint("backup") as sp_session:
            await User.create(email="invalid@example.com", session=sp_session)
    except Exception:
        print("Savepoint rolled back, outer transaction continues")
```

### Relationships

```python
class User(Model):
    name: Mapped[str] = mapped_column(String(100))

class Post(Model):
    title: Mapped[str] = mapped_column(String(255))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    
    # Define relationship
    user: Mapped[User] = relationship("User", back_populates="posts")

class User(Model):
    name: Mapped[str] = mapped_column(String(100))
    posts: Mapped[List["Post"]] = relationship("Post", back_populates="user")

# Query with relationships
user = await User.query().joinedload("posts").first()

# Access relationship (no DB call since it was eager-loaded)
for post in user.posts:
    print(post.title)
```

### Many-to-Many Relationships

```python
class Article(Model):
    title: Mapped[str] = mapped_column(String(255))

class Tag(Model):
    name: Mapped[str] = mapped_column(String(50), unique=True)

class ArticleTag(Model):  # Through model (optional but recommended)
    __tablename__ = "article_tags"
    article_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("articles.id"), primary_key=True)
    tag_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tags.id"), primary_key=True)

# Query with M2M
article = await Article.query().selectinload("tags").first()
print([tag.name for tag in article.tags])
```

## Architecture Diagrams

### Session Resolution Flow

```
QuerySet.__init__(model, session)
    ↓
Is session a Database?
    ├─ Yes: Model._bind_db(session) + use session_factory
    └─ No: Check if AsyncSession
        ├─ Yes: Use it
        └─ No: Continue to next step
    ↓
Is session passed?
    ├─ Yes: Use it
    └─ No: Get from async context (get_session())
    ↓
No session in context?
    ├─ db_strict_session_mode=True: Raise SessionResolutionError
    └─ db_strict_session_mode=False: Create temporary session
```

### RBAC Filter Flow

```
QuerySet.all() or .filter()
    ↓
_apply_rbac(action="read")
    ↓
Model.__rbac__[action] = rule
    ↓
rule.resolve(model_cls, current_user)
    ├─ Returns: True → No filter (allow all)
    ├─ Returns: False → WHERE false (deny all)
    └─ Returns: ColumnElement → WHERE condition (specific filter)
    ↓
Add WHERE clause to statement
    ↓
Execute query
```

### Model Initialization Flow

```
class User(Model):
    ...
    ↓
Model.__init_subclass__()
    ↓
SchemaInferenceEngine.process_class()
    ├─ Infer column types
    ├─ Process foreign keys
    └─ Set up relationships
    ↓
ValidationScanner.discover_rules()
    ├─ Find validation decorators
    └─ Register rules
    ↓
Tenancy check: tenant_id in fields?
    ├─ Yes: Register with tenancy_registry
    └─ No: Continue
    ↓
Register update timestamp listener
    ↓
Complete
```

## Best Practices

### 1. Always Use Transactions for Multiple Operations

```python
# ❌ BAD: No transaction, intermediate failure loses consistency
await User.create(email="user1@example.com")
await Profile.create(user_id=user.id)

# ✅ GOOD: Wrapped in transaction
async with db.transaction() as session:
    user = await User.create(email="user1@example.com", session=session)
    await Profile.create(user_id=user.id, session=session)
```

### 2. Use Validation & Signals for Business Logic

```python
# ❌ BAD: Business logic scattered in view
if email_exists(email):
    raise ValidationError("Email already exists")
user = await User.create(email=email)

# ✅ GOOD: Encapsulated in signals
@pre_save.connect
async def validate_unique_email(sender, instance, is_new, session):
    if is_new and await User.query(session).filter(email=instance.email).exists():
        raise ValidationError("Email already exists")
```

### 3. Use Eager Loading for Relationships

```python
# ❌ BAD: N+1 query problem
posts = await Post.query().all()
for post in posts:
    author = await User.query().filter(id=post.user_id).first()  # DB call per post!

# ✅ GOOD: Eager load relationships
posts = await Post.query().joinedload("user").all()
for post in posts:
    author = post.user  # Already loaded, no DB call
```

### 4. Respect RBAC in Queries

```python
# ❌ BAD: Bypass RBAC
all_posts = await Post.query(session).all()  # No RBAC filtering!

# ✅ GOOD: Rely on RBAC (if configured)
visible_posts = await Post.query().all()  # Automatically filtered by current user
```

### 5. Use Type Hints

```python
# ✅ GOOD: Clear types
async def get_user(user_id: uuid.UUID, session: AsyncSession) -> Optional[User]:
    return await User.query(session).filter(id=user_id).first()

@post_save.connect
async def notify_user(sender: Type[Model], instance: Any, is_new: bool, session: AsyncSession) -> None:
    if is_new:
        await send_email(instance.email, "Welcome!")
```

## Troubleshooting

### "SessionResolutionError: Failed to resolve database session"

**Cause**: QuerySet couldn't find a session and `db_strict_session_mode=True`

**Solution**: Pass session explicitly or bind database globally
```python
# Option 1: Explicit session
async with db.transaction() as session:
    user = await User.query(session).first()

# Option 2: Bind globally (in app startup)
await db.connect()
```

### "Column 'X' does not exist"

**Cause**: Model changes not reflected in schema

**Solution**: Run migrations or recreate tables
```python
# In startup
await db.connect(create_tables=True)  # Recreate all tables
```

### "DetachedInstanceError: Attribute 'X' not loaded"

**Cause**: Relationship not eager-loaded before session closed

**Solution**: Use `selectinload()` or `joinedload()`
```python
user = await User.query().selectinload("posts").first()
print(user.posts)  # Now safe, posts already loaded
```

### RBAC Not Filtering Results

**Cause**: Model doesn't have `__rbac__` rules for that action

**Solution**: Define RBAC rules
```python
class Post(Model):
    user_id: Mapped[uuid.UUID]
    
    __rbac__ = {
        "read": AllowAuthenticated(),
        "update": AllowOwner("user_id"),
    }
```

## See Also

- [Migration Guide](./orm-migrations.md)
- [Validation Guide](./forms.md)
- [Multi-Tenancy Guide](./multi-tenancy-masterclass.md)
- [Query Reference](./orm-querying.md)
