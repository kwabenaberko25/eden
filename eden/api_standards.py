r'''
Eden API Consistency & Standards

This guide documents the standard patterns for:
1. Template Rendering
2. Error Response Format
3. Model Inheritance
4. API Response Conventions

═══════════════════════════════════════════════════════════════════════════════

1. TEMPLATE RENDERING

Both of these are equivalent and correct. Use whichever fits your style:

Option A: Standalone Function (Simpler)
───────────────────────────────────────

    from eden.templating import render_template
    
    @app.get("/")
    async def home(request):
        return render_template(
            "home.html",
            title="Home Page",
            user=request.user,
            featured_posts=await Post.filter(featured=True).all()
        )

Pros:
- Cleaner syntax
- Works in context (request injected via middleware)
- Less typing

Cons:
- Requires request context to be set (middleware or context var)

Option B: Request Method (Explicit)
───────────────────────────────────

    @app.get("/")
    async def home(request):
        return request.app.render(
            "home.html",
            title="Home Page",
            user=request.user
        )

Pros:
- Explicit (no hidden request lookup)
- Works anywhere with request object

Cons:
- More verbose

RECOMMENDATION: Use render_template() in route handlers.
The request context is guaranteed to be set.

Both automatically inject: request, user (if authenticated), tenant (if multi-tenant)

    # In template:
    {{ request.url.path }}        # Current path
    {{ request.method }}          # GET, POST, etc.
    {{ user.name if user }}       # Current user
    {{ tenant.name if tenant }}   # Current tenant
    {{ csrf_token }}              # CSRF token for forms

═══════════════════════════════════════════════════════════════════════════════

2. ERROR RESPONSE FORMAT

Eden uses a consistent error response format across all APIs.

Standard Error Response Structure:
──────────────────────────────────

    {
        "error": true,
        "status": 400,
        "code": "VALIDATION_ERROR",
        "message": "Invalid input",
        "detail": "Field 'email' is required",
        "errors": [
            {
                "field": "email",
                "message": "Field is required",
                "code": "REQUIRED"
            },
            {
                "field": "age",
                "message": "Must be >= 18",
                "code": "VALIDATION_ERROR"
            }
        ]
    }

Always use JsonResponse with status_code for consistency:

    from eden.responses import JsonResponse, json
    
    # Method 1: Using json() shortcut
    return json(
        {
            "error": True,
            "message": "User not found"
        },
        status_code=404
    )
    
    # Method 2: Using JsonResponse class
    return JsonResponse(
        {
            "error": True,
            "message": "Invalid email"
        },
        status_code=400
    )

Common HTTP Status Codes:
────────────────────────

    400 Bad Request         Input validation failed
    401 Unauthorized        Missing or invalid authentication
    403 Forbidden           Authenticated but no permission
    404 Not Found           Resource doesn't exist
    409 Conflict            Resource already exists (duplicate)
    422 Unprocessable       Request well-formed but contains errors
    500 Internal Server     Unexpected server error
    503 Service Unavailable Temporarily unavailable

Error Response Examples:
─────────────────────────

    # Validation Error
    return json(
        {
            "error": True,
            "code": "VALIDATION_ERROR",
            "message": "Validation failed",
            "errors": [
                {"field": "email", "message": "Invalid email format"}
            ]
        },
        status_code=422
    )
    
    # Authentication Error
    return json(
        {
            "error": True,
            "code": "UNAUTHORIZED",
            "message": "Invalid credentials"
        },
        status_code=401
    )
    
    # Not Found Error
    return json(
        {
            "error": True,
            "code": "NOT_FOUND",
            "message": f"User {user_id} not found"
        },
        status_code=404
    )
    
    # Success Response (for contrast)
    return json(
        {
            "error": False,  # or omit this for success responses
            "data": {
                "id": 123,
                "name": "Alice"
            }
        },
        status_code=200
    )

════════════════════════════════════════════════════════════════════════════════

3. MODEL INHERITANCE

Eden supports three patterns for model inheritance:

Pattern 1: Abstract Base Model
──────────────────────────────
Base model with shared fields. Subclasses get their own tables.

    from eden.db import Model
    from eden.db.fields import StringField, DateTimeField
    
    class BaseModel(Model):
        __abstract__ = True  # Important!
        
        created_at: Mapped[datetime] = DateTimeField(auto_now_add=True)
        updated_at: Mapped[datetime] = DateTimeField(auto_now=True)
    
    class User(BaseModel):
        __tablename__ = "users"
        
        name: Mapped[str] = StringField(max_length=100)
        email: Mapped[str] = StringField(max_length=254, unique=True)
    
    class Post(BaseModel):
        __tablename__ = "posts"
        
        title: Mapped[str] = StringField(max_length=200)
        content: Mapped[str] = TextField()

Result: Two separate tables (users, posts), each with created_at/updated_at.

Pros:
- Code reuse (shared fields)
- Simple queries (no JOINs)

Cons:
- Duplicate columns (created_at in both tables)
- Can't query abstract base directly

Pattern 2: Mixin Classes
────────────────────────
Reusable functionality added to models.

    class TimestampMixin:
        """Adds created_at and updated_at to any model."""
        created_at: Mapped[datetime] = DateTimeField(auto_now_add=True)
        updated_at: Mapped[datetime] = DateTimeField(auto_now=True)
    
    class SoftDeleteMixin:
        """Adds soft delete (mark as deleted, don't remove from DB)."""
        deleted_at: Mapped[datetime | None] = DateTimeField(nullable=True)
        
        @classmethod
        def _base_select(cls):
            # Automatically exclude soft-deleted records in queries
            stmt = select(cls)
            if hasattr(cls, "deleted_at"):
                stmt = stmt.where(cls.deleted_at.is_(None))
            return stmt
    
    class User(TimestampMixin, SoftDeleteMixin, Model):
        __tablename__ = "users"
        
        name: Mapped[str] = StringField(max_length=100)
    
    # Usage
    await User.all()  # Excludes soft-deleted users automatically
    
    # Soft delete
    await user.update(deleted_at=datetime.now())
    
    # Hard delete
    await user.delete(hard=True)

Pros:
- Flexible (can mix and match)
- Clear intent (name tells what it does)
- Reusable across projects

Cons:
- Requires proper __mro__ (method resolution order)
- Multiple inheritance can be complex

Pattern 3: Single Table Inheritance
────────────────────────────────────
Subclasses share one table with a type discriminator.

    class Animal(Model):
        __tablename__ = "animals"
        
        id: Mapped[int] = IntField(primary_key=True)
        type: Mapped[str] = StringField(max_length=50)  # Discriminator
        name: Mapped[str] = StringField(max_length=100)
        
        __mapper_args__ = {
            "polymorphic_identity": "animal",
            "polymorphic_on": type,
        }
    
    class Dog(Animal):
        breed: Mapped[str | None] = StringField(max_length=50, nullable=True)
        
        __mapper_args__ = {
            "polymorphic_identity": "dog",
        }
    
    class Cat(Animal):
        indoor: Mapped[bool] = BoolField(default=True)
        
        __mapper_args__ = {
            "polymorphic_identity": "cat",
        }
    
    # Usage
    animals = await Animal.all()  # Returns mix of Dog and Cat instances
    dogs = await Dog.all()  # Only dogs
    
    # Create instances
    dog = Dog(name="Buddy", breed="Golden Retriever")
    cat = Cat(name="Whiskers", indoor=True)

Result: Single "animals" table with:
    id, type, name, breed (nullable), indoor (nullable)

type = "dog" or "cat" determines which class is instantiated.

Pros:
- Efficient (single table, no JOINs)
- Query all subtypes at once
- Good for simple hierarchies

Cons:
- All columns nullable for different types
- More design upfront
- Hard to add type-specific constraints

RECOMMENDATION:
- Use TimestampMixin + SoftDeleteMixin for most models
- Use abstract base for related model groups
- Single table inheritance only if polymorphic queries are needed

════════════════════════════════════════════════════════════════════════════════

4. API RESPONSE CONVENTIONS

Consistent response format across your API:

Success Response (200 OK):
──────────────────────────

    # Single resource
    return json(
        {
            "id": 123,
            "name": "Alice",
            "email": "alice@example.com"
        }
    )
    
    # Multiple resources with pagination
    return json(
        {
            "data": [
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"}
            ],
            "pagination": {
                "total": 42,
                "page": 1,
                "per_page": 20,
                "has_more": True
            }
        }
    )

Created Response (201 Created):
───────────────────────────────

    resource = User(name="Alice", email="alice@example.com")
    await resource.save()
    
    return json(
        {"id": resource.id, "name": resource.name},
        status_code=201
    )

Accepted Response (202 Accepted):
──────────────────────────────────
For async operations (background jobs, etc.):

    job = await queue_background_job(...)
    
    return json(
        {
            "job_id": job.id,
            "status": "pending",
            "check_url": f"/jobs/{job.id}"
        },
        status_code=202
    )

Updated Response (200 OK):
──────────────────────────

    updated = await User.filter(id=id).update(name="New Name")
    user = await User.get(id)
    
    return json({"id": user.id, "name": user.name})

Deleted Response (204 No Content):
──────────────────────────────────

    await User.filter(id=id).delete()
    
    return Response(status_code=204)  # Empty body

Batch Operation Response:
─────────────────────────

    # Bulk operations show what happened
    return json(
        {
            "success": 45,
            "failed": 5,
            "errors": [
                {"row": 1, "error": "Duplicate email"},
                {"row": 3, "error": "Invalid age"}
            ]
        }
    )

════════════════════════════════════════════════════════════════════════════════

COMPLETE EXAMPLE: Following all standards

    from eden.templating import render_template
    from eden.responses import json, JsonResponse
    from eden.dependencies import Depends
    
    async def get_current_user(request) -> Any:
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            return None
        return await User.filter(auth_token=token).first()
    
    # HTML Response (uses render_template)
    @app.get("/posts")
    async def list_posts(request) -> Any:
        posts = await Post.filter(published=True).order_by("-created_at").all()
        return render_template("posts/list.html", posts=posts)
    
    # JSON Response - Success
    @app.get("/api/posts/{post_id}")
    async def get_post_api(post_id: int) -> Any:
        post = await Post.get(post_id)
        if not post:
            return json(
                {"error": True, "message": f"Post {post_id} not found"},
                status_code=404
            )
        return json(post.to_dict())  # 200 OK
    
    # JSON Response - with validation
    @app.post("/api/posts")
    async def create_post(
        request,
        user=Depends(get_current_user)
    ):
        if not user:
            return json(
                {"error": True, "message": "Authentication required"},
                status_code=401
            )
        
        data = await request.json()
        
        # Validate input
        if not data.get("title"):
            return json(
                {
                    "error": True,
                    "code": "VALIDATION_ERROR",
                    "errors": [{"field": "title", "message": "Title is required"}]
                },
                status_code=422
            )
        
        # Create resource
        post = Post(
            title=data["title"],
            content=data.get("content", ""),
            author_id=user.id
        )
        await post.save()
        
        return json(post.to_dict(), status_code=201)
    
    # Model with best practices
    class Post(TimestampMixin, SoftDeleteMixin, Model):
        __tablename__ = "posts"
        
        id: Mapped[uuid.UUID] = UUIDField(primary_key=True)
        title: Mapped[str] = StringField(max_length=200)
        content: Mapped[str] = TextField()
        published: Mapped[bool] = BoolField(default=False)
        author_id: Mapped[uuid.UUID] = UUIDField(foreign_key="users.id")
        author: Mapped[User] = relationship("User")
        
        def to_dict(self):
            return {
                "id": str(self.id),
                "title": self.title,
                "content": self.content,
                "published": self.published,
                "author_id": str(self.author_id),
                "created_at": self.created_at.isoformat(),
                "updated_at": self.updated_at.isoformat(),
            }

════════════════════════════════════════════════════════════════════════════════
'''

# This is documentation only. No implementation needed.
