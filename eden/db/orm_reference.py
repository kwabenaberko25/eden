"""
Eden ORM — Django-Compatible API Reference

Eden's QuerySet provides a Django-like API with async/await support.
This module serves as reference documentation for all ORM methods.

Quick Start:
    from eden.db import Model
    from eden.db.fields import StringField, DateTimeField, IntField
    
    class User(Model):
        __tablename__ = "users"
        name: str = StringField(max_length=100)
        email: str = StringField(max_length=254, unique=True)
        age: int = IntField(nullable=True)
    
    # Querying
    users = await User.all()                        # Get all users
    user = await User.filter(name="Alice").first()  # Single filter
    young = await User.filter(age__lt=30).all()     # Comparison operators
    active = await User.filter(is_active=True).count()  # Count results
    
    # Pagination
    page = await User.paginate(page=2, per_page=20)
    print(page.links)  # {"self": ..., "next": ..., "prev": ...}
    
    # Aggregation
    stats = await User.aggregate(total=Count("id"), avg_age=Avg("age"))
    
    # Mutations
    updated = await User.filter(email="old@example.com").update(email="new@example.com")
    deleted = await User.filter(age__gt=100).delete()

═══════════════════════════════════════════════════════════════════════════════

FILTERING

filter(**lookups) → QuerySet
    Filter rows matching all conditions (AND logic).
    
    Django equivalent: Model.objects.filter(**lookups)
    
    Supported lookups:
        __exact or no suffix    Exact match: User.filter(id=1)
        __iexact                Case-insensitive: filter(name__iexact="alice")
        __contains              Substring match: filter(bio__contains="Python")
        __icontains             Case-insensitive substring: filter(name__icontains="alice")
        __startswith            Starts with: filter(email__startswith="alice")
        __istartswith           Case-insensitive: filter(name__istartswith="alice")
        __endswith              Ends with: filter(email__endswith="@example.com")
        __iendswith             Case-insensitive: filter(name__iendswith="son")
        __gt, __gte             Greater than / >=: filter(age__gt=18)
        __lt, __lte             Less than / <=: filter(age__lte=65)
        __in                    IN clause: filter(status__in=["active", "pending"])
        __range                 BETWEEN: filter(age__range=(18, 65))
        __isnull                NULL check: filter(deleted_at__isnull=False)
    
    Q objects support complex AND/OR/NOT logic:
        from eden.db import Q
        await User.filter(Q(age__lt=18) | Q(is_admin=True)).all()
        await User.filter(~Q(status="banned")).all()
    
    Examples:
        # Simple filters
        await User.filter(active=True).all()
        await User.filter(name="Alice", email="alice@example.com").all()
        
        # Lookups
        await User.filter(age__gte=18).all()
        await User.filter(email__icontains="gmail").all()
        await User.filter(created_at__range=(start_date, end_date)).all()
        
        # Relationships
        await Post.filter(author__name__icontains="alice").all()
        
        # Complex logic with Q
        await User.filter(
            Q(is_admin=True) | Q(is_moderator=True)
        ).exclude(banned=True).all()

exclude(**lookups) → QuerySet
    Filter rows NOT matching conditions (opposite of filter()).
    
    Django equivalent: Model.objects.exclude(**lookups)
    
    Examples:
        await User.exclude(status="banned").all()
        await Post.exclude(author__is_active=False).all()

═══════════════════════════════════════════════════════════════════════════════

RETRIEVAL

all() → List[T]
    Fetch all matching rows. Returns empty list if none found.
    
    Django equivalent: Model.objects.all()
    
    await User.all()  # All users
    await User.filter(active=True).all()  # All active users

first() → T | None
    Fetch first matching row, or None if none found.
    
    Django equivalent: Model.objects.first()
    
    first_user = await User.first()

last() → T | None
    Fetch last matching row (ordered by ID).
    
    Django equivalent: Model.objects.last()
    
    last_user = await User.last()

get(id=...) → T | None
    Fetch row by primary key, or None if not found.
    
    Django equivalent: Model.objects.get(pk=...)
    
    user = await User.get(123)  # By ID
    
get_or_404(**filters) → T
    Fetch matching row, or raise 404 if not found.
    
    Example:
        user = await User.get_or_404(slug="alice")

filter_one(**filters) → T | None
    Shorthand for filter().first()
    
    user = await User.filter_one(email="alice@example.com")

get_or_create(defaults=None, **filters) → (T, bool)
    Get row matching filters, or create new one.
    Returns: (instance, created_flag)
    
    Django equivalent: Model.objects.get_or_create(**filters, defaults=defaults)
    
    user, created = await User.get_or_create(
        email="alice@example.com",
        defaults={"name": "Alice", "age": 25}
    )
    if created:
        print("New user created")

count() → int
    Count matching rows.
    
    Django equivalent: Model.objects.count()
    
    active_users = await User.filter(active=True).count()

exists() → bool
    Check if any rows match (more efficient than count() > 0).
    
    Django equivalent: Model.objects.exists()
    
    admin_exists = await User.filter(is_admin=True).exists()

═══════════════════════════════════════════════════════════════════════════════

ORDERING & PAGINATION

order_by(*fields) → QuerySet
    Sort results by fields. Prefix with - for descending.
    
    Django equivalent: Model.objects.order_by(...)
    
    Examples:
        await User.order_by("name").all()          # A→Z
        await User.order_by("-created_at").all()   # Newest first
        await User.order_by("age", "-name").all()  # Age (low→high), then name (Z→A)

limit(n) → QuerySet
    Limit to n rows (LIMIT clause).
    
    Django equivalent: Model.objects.all()[:n]
    
    first_10 = await User.limit(10).all()

offset(n) → QuerySet
    Skip first n rows (OFFSET clause).
    
    Django equivalent: Model.objects.all()[n:]
    
    page_2 = await User.order_by("id").offset(20).limit(10).all()

paginate(page=1, per_page=20) → Page[T]
    Fetch paginated results with HATEOAS links.
    
    Django equivalent: (use django-rest-framework)
    
    page = await User.paginate(page=2, per_page=50)
    print(page.items)       # List of users
    print(page.total)       # Total count
    print(page.links)       # {"self": ..., "next": ..., "prev": ...}

═══════════════════════════════════════════════════════════════════════════════

MUTATIONS

update(**kwargs) → int
    Update all matching rows, return count updated.
    
    Django equivalent: Model.objects.filter(...).update(**kwargs)
    
    updated = await User.filter(status="pending").update(status="active")
    print(f"Updated {updated} users")  # Updated 5 users
    
    Use F() expressions for column-level operations:
        from eden.db import F
        await User.update(login_count=F("login_count") + 1)

delete(hard=False) → int
    Delete matching rows, return count deleted.
    
    Django equivalent: Model.objects.filter(...).delete()
    
    Soft delete (if SoftDeleteMixin):
        deleted = await User.filter(status="inactive").delete()  # Marks deleted_at
    
    Hard delete (physically remove):
        deleted = await User.filter(id__in=[1,2,3]).delete(hard=True)

bulk_create(objects, batch_size=100) → int
    Create multiple rows efficiently in batches.
    
    Django equivalent: Model.objects.bulk_create(...)
    
    users = [
        User(name="Alice", email="alice@example.com"),
        User(name="Bob", email="bob@example.com"),
        User(name="Charlie", email="charlie@example.com"),
    ]
    created = await User.bulk_create(users, batch_size=100)
    print(f"Created {created} users")

═══════════════════════════════════════════════════════════════════════════════

AGGREGATION & ANNOTATION

aggregate(**agg) → dict
    Compute aggregate values (COUNT, SUM, AVG, MIN, MAX, etc.).
    
    Django equivalent: Model.objects.aggregate(...)
    
    from eden.db import Count, Sum, Avg, Min, Max
    
    stats = await User.aggregate(
        total=Count("id"),
        avg_age=Avg("age"),
        oldest_user_id=Max("id")
    )
    print(stats)  # {"total": 42, "avg_age": 32.5, "oldest_user_id": 123}

annotate(**annotations) → QuerySet
    Add computed columns to each row (like GROUP BY in SQL).
    
    Django equivalent: Model.objects.annotate(...)
    
    from eden.db import Count, F, Q
    
    # Example: Get user count per post
    posts = await Post.annotate(
        comment_count=Count("comments")
    ).all()
    
    for post in posts:
        print(f"{post.title}: {post.comment_count} comments")

═══════════════════════════════════════════════════════════════════════════════

RELATIONSHIPS

prefetch(*relationships) → QuerySet
    Pre-load related objects to avoid N+1 queries.
    
    Django equivalent: Model.objects.prefetch_related(...)
    
    # Without prefetch: N+1 query problem
    users = await User.all()
    for user in users:
        print(user.profile.bio)  # Executes 1 query per user! (N=51 queries)
    
    # With prefetch: 2 queries total
    users = await User.prefetch("profile").all()
    for user in users:
        print(user.profile.bio)  # No extra queries!
    
    # Deep relationships
    users = await User.prefetch("profile", "posts", "posts.comments").all()

═══════════════════════════════════════════════════════════════════════════════

VALUES & CACHING

values(*fields) → QuerySet[dict]
    Return dicts instead of model instances (lightweight query).
    
    Django equivalent: Model.objects.values(...)
    
    data = await User.values("id", "name", "email").all()
    # Returns: [{"id": 1, "name": "Alice", ...}, ...]
    
    # Useful for JSON APIs
    return JsonResponse(data)

cache(ttl=300) → QuerySet
    Cache query results for ttl seconds.
    
    # First call: hits database
    users = await User.filter(active=True).cache(ttl=60).all()
    
    # Within 60 seconds: returns cached list
    users = await User.filter(active=True).cache(ttl=60).all()
    
    Note: Requires redis or in-memory backend configured

═══════════════════════════════════════════════════════════════════════════════

RBAC & TENANT FILTERING

for_user(user, action="read") → QuerySet
    Filter rows visible to specific user (RBAC-aware).
    
    # Get posts user can read
    posts = await Post.for_user(current_user, action="read").all()
    
    # Get posts user can edit
    editable = await Post.for_user(current_user, action="update").all()

═══════════════════════════════════════════════════════════════════════════════

CHAINING EXAMPLES

Queries chain fluently:

    # Complex query
    posts = await (Post
        .filter(author__is_active=True)
        .exclude(status="draft")
        .filter(published_at__isnull=False)
        .order_by("-published_at")
        .prefetch("author", "comments")
        .limit(10)
        .all()
    )

    # Pagination with filters
    page = await (User
        .filter(active=True)
        .order_by("name")
        .paginate(page=2, per_page=20)
    )

═══════════════════════════════════════════════════════════════════════════════

TRANSACTION CONTEXT

Use @atomic decorator or transaction context manager:

    from eden.db import atomic
    
    @app.post("/")
    @atomic  # Auto-wraps in transaction
    async def create_user():
        user = User(name="Alice")
        await user.save()
        return {"id": user.id}

Or manual transactions:

    from eden.db import transaction
    
    async with transaction():
        user = User(name="Alice")
        await user.save()
    # Auto-commit on exit, rollback on error
"""

# This is documentation only. No implementation code is needed here.
# All methods are implemented in eden.db.query.QuerySet
