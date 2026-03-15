# Routing System 🛣️

Eden's routing system is designed to be expressive, hierarchical, and type-safe.

> **Advanced Routing?** See [Advanced Routing with Metadata](advanced-routing.md) for named routes, tags, route-specific middleware, RBAC, versioning, and dynamic route generation.

## Basic Routing

Routes are defined using decorators on the `app` instance.

```python
@app.get("/")
async def home(request):
    return {"page": "Home"}

@app.post("/submit")
async def handle_submit(request):
    data = await request.form()
    return {"status": "received"}
```

Supported methods: `@app.get()`, `@app.post()`, `@app.put()`, `@app.patch()`, `@app.delete()`.

## The `@app` Decorators

Eden uses intuitive decorators for route registration.

```python
@app.get("/")
async def get_user(request, user_id: int):
    # user_id is automatically cast to an integer
    return {"id": user_id}
```

### Parameter Types

| Type | Syntax | Description |
| :--- | :--- | :--- |
| `str` | `{name}` | Captures as a string (default). |
| `int` | `{id:int}` | Captures and casts to integer. |
| `float` | `{val:float}` | Captures and casts to float. |
| `uuid` | `{id:uuid}` | Captures and casts to a UUID object. |
| `path` | `{file:path}` | Captures everything, including slashes. |

### Path Parameters in Practice

```python
# Single parameter
@app.get("/posts/{id:int}")
async def get_post(request, id: int):
    post = await Post.get(id=id)
    if not post:
        return {"error": "Not found"}, 404
    return post.to_dict()

# Multiple parameters (commonly used for relationships)
@app.get("/users/{user_id:int}/posts/{post_id:int}")
async def get_user_post(request, user_id: int, post_id: int):
    user = await User.get(id=user_id)
    if not user:
        return {"error": "User not found"}, 404
    
    post = await Post.get(id=post_id, user_id=user_id)
    if not post:
        return {"error": "Post not found"}, 404
    return post.to_dict()

# Slug-based (common for SEO)
@app.get("/blog/{slug}")
async def get_blog_post(request, slug: str):
    post = await BlogPost.get_by(slug=slug)
    return request.render("post.html", {"post": post})

# Path parameters (captures entire remaining path)
@app.get("/files/{filepath:path}")
async def serve_file(request, filepath: str):
    return FileResponse(f"uploads/{filepath}")
```

---

## Query Parameters

Query parameters are accessed via `request.query_params`:

```python
# Single query parameter
@app.get("/search")
async def search(request):
    q = request.query_params.get("q", "")  # Default to ""
    results = await Post.filter(title__contains=q)
    return {"results": [r.to_dict() for r in results]}

# Multiple query parameters
@app.get("/products")
async def list_products(request):
    page = int(request.query_params.get("page", 1))
    per_page = int(request.query_params.get("per_page", 20))
    sort_by = request.query_params.get("sort", "created_at")
    
    products = await Product.filter(
        is_active=True
    ).order_by(sort_by).limit(per_page).offset((page-1)*per_page)
    
    return {
        "products": [p.to_dict() for p in products],
        "page": page,
        "total": await Product.count()
    }

# Filter with query parameters (REST API pattern)
@app.get("/users")
async def list_users(request):
    filters = {}
    
    # Build filters from query params
    if request.query_params.get("role"):
        filters["role"] = request.query_params.get("role")
    if request.query_params.get("is_active"):
        filters["is_active"] = request.query_params.get("is_active").lower() == "true"
    
    users = await User.filter(**filters)
    return {"users": [u.to_dict() for u in users]}
```

---

## Request Body & POST Data

```python
# JSON request body
@app.post("/posts")
async def create_post(request):
    data = await request.json()
    
    post = await Post.create(
        title=data["title"],
        content=data["content"],
        author_id=request.user.id
    )
    
    return {"post": post.to_dict()}, 201

# Form data (HTML forms)
@app.post("/contact")
async def submit_contact(request):
    form_data = await request.form()
    
    message = await Message.create(
        name=form_data.get("name"),
        email=form_data.get("email"),
        body=form_data.get("message")
    )
    
    return {"status": "Message saved"}, 201

# File uploads
@app.post("/upload")
async def upload_file(request):
    form_data = await request.form()
    file = form_data.get("file")  # UploadedFile object
    
    # Access file properties
    print(f"Filename: {file.filename}")
    print(f"Content type: {file.content_type}")
    print(f"Size: {file.size} bytes")
    
    # Save file
    file_path = f"uploads/{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())
    
    return {"filename": file.filename}, 201
```

---

## Status Codes & Responses

Use appropriate HTTP status codes for clarity:

```python
from eden import status

# 2xx Success
@app.post("/tasks")
async def create_task(request):
    data = await request.json()
    task = await Task.create(**data)
    return {"task": task.to_dict()}, status.HTTP_201_CREATED

# 3xx Redirects
@app.get("/old-path")
async def old_url(request):
    return redirect("/new-path", status_code=status.HTTP_301_MOVED_PERMANENTLY)

# 4xx Client Errors
@app.get("/posts/{id:int}")
async def get_post(request, id: int):
    post = await Post.get(id=id)
    if not post:
        return {"error": "Post not found"}, status.HTTP_404_NOT_FOUND
    
    if not request.user or not user_can_view(request.user, post):
        return {"error": "Access denied"}, status.HTTP_403_FORBIDDEN
    
    return post.to_dict()

# 5xx Server Errors (typically not explicit, but for custom error handling)
@app.get("/dangerous-operation")
async def dangerous(request):
    try:
        result = await risky_database_query()
        return result
    except DatabaseError as e:
        return {
            "error": "Database operation failed",
            "details": str(e)
        }, status.HTTP_500_INTERNAL_SERVER_ERROR
```

---

## Sub-Routers

As your application grows, you can split your routes into separate modules using the `Router` class.

### Basic Router Organization

```python
# routes/api/users.py
from eden import Router
from app.models import User

users_router = Router(name="users")

@users_router.get("/", name="list")
async def list_users():
    users = await User.all()
    return [user.to_dict() for user in users]

@users_router.get("/{id:int}", name="detail")
async def get_user(id: int):
    user = await User.get(id=id)
    if not user:
        return {"error": "Not found"}, 404
    return user.to_dict()

@users_router.post("/", name="create")
async def create_user(request):
    data = await request.json()
    user = await User.create(**data)
    return {"user": user.to_dict()}, 201

# routes/api/__init__.py
from eden import Router
from .users import users_router

api_router = Router(name="api", prefix="/api/v1")
api_router.include_router(users_router, prefix="/users")

# app.py
app.include_router(api_router)
```

Now your routes are available at:
- `GET /api/v1/users` (via `api:users:list`)
- `GET /api/v1/users/{id}` (via `api:users:detail`)
- `POST /api/v1/users` (via `api:users:create`)

### Router-Level Middleware

```python
from starlette.middleware.base import BaseHTTPMiddleware

class RequireAuth(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if not request.user or not request.user.is_authenticated:
            return {"error": "Unauthorized"}, 401
        return await call_next(request)

# Apply middleware to entire router
admin_router = Router(name="admin", prefix="/admin")
admin_router.add_middleware(RequireAuth)

@admin_router.get("/stats", name="stats")
async def admin_stats(request):
    # This handler always has authenticated user
    return {"user": request.user.id}
```

---

## Request Validation with Schemas

The Eden way is to validate request data using Schemas declaratively:

```python
from eden.forms import Schema, field, EmailStr

class CreateUserSchema(Schema):
    name: str = field(min_length=2, max_length=100)
    email: EmailStr = field()
    password: str = field(min_length=8)

# Handler using validated schema
@app.post("/users")
async def create_user_validated(request, data: CreateUserSchema):
    # By the time your handler runs:
    # - data is validated
    # - types are correct
    # - data.to_dict() can be passed directly to create()
    
    user = await User.create(**data.to_dict())
    return {"user": user.to_dict()}, 201

# Or use the decorator for auto-error handling
@app.post("/users")
@app.validate(CreateUserSchema)
async def create_user_decorated(request, data: CreateUserSchema):
    # If validation fails, Eden automatically returns 422 with errors
    # If valid, data is injected already validated
    user = await User.create(**data.to_dict())
    return {"user": user.to_dict()}, 201
```

### Complex Validation

```python
from pydantic import model_validator

class UpdateProductSchema(Schema):
    title: str = field(min_length=1)
    price: float = field(gt=0)
    stock: int = field(ge=0)
    
    @model_validator(mode="after")
    def validate_business_logic(self):
        """Check cross-field constraints."""
        # Premium products must have stock
        if self.price > 1000 and self.stock == 0:
            raise ValueError("High-value items must have stock > 0")
        return self

@app.put("/products/{id:int}")
@app.validate(UpdateProductSchema)
async def update_product(request, id: int, data: UpdateProductSchema):
    product = await Product.get(id=id)
    if not product:
        return {"error": "Not found"}, 404
    
    await product.update(**data.to_dict())
    return {"product": product.to_dict()}
```

---

## Error Handling

### Exception Handlers

```python
from eden.exceptions import HTTPException

# Global exception handler
@app.exception_handler(ValueError)
async def handle_value_error(request, exc):
    return {
        "error": "Invalid value",
        "details": str(exc)
    }, 400

# Handle specific entity not found
@app.exception_handler(404)
async def handle_not_found(request, exc):
    return {
        "error": "Resource not found",
        "path": request.url.path
    }, 404

# Raise exceptions from handlers
@app.get("/posts/{id:int}")
async def get_post(request, id: int):
    post = await Post.get(id=id)
    if not post:
        raise HTTPException(
            status_code=404,
            detail=f"Post {id} not found"
        )
    return post.to_dict()
```

### Conditional Error Responses

```python
@app.post("/payments")
async def process_payment(request):
    data = await request.json()
    
    try:
        result = await payment_service.charge(
            amount=data["amount"],
            token=data["token"]
        )
        return {"transaction_id": result.id}, 200
    
    except payment_service.InsufficientFunds:
        return {"error": "Insufficient funds"}, 402
    except payment_service.InvalidCard:
        return {"error": "Card declined"}, 400
    except payment_service.NetworkError:
        return {
            "error": "Payment processing temporarily unavailable",
            "retry_after": 60
        }, 503
```

---

## Namespaced Routing

Eden's namespaces allow you to group related routes and generate clean, reverse-able URLs. When you include a router with a `name`, it creates a namespace.

```python
# routes/auth.py
router = Router(name="auth")

@router.get("/login", name="login")
async def login(request):
    ...
```

### URL Generation in Templates

Instead of hardcoding URLs, use the `@url` template directive to dynamically generate paths based on route names and namespaces.

```html
<!-- Sign In link -->
<a href="@url('auth:login')">Sign In</a>

<!-- Link with parameters -->
<a href="@url('users:profile', id=user.id)">View Profile</a>
```

---

## Recursive Middleware

Eden allows you to apply middleware to specific sub-routers, providing granular control over your application's security and behavior.

```python
from eden.middleware import AuthMiddleware

api_router = Router()
api_router.add_middleware(AuthMiddleware)

@api_router.get("/v1/profile")
async def profile(request):
    return request.user
```

---

## HTMX & Targeted Fragments

One of Eden's elite features is the ability to render specific template sections (fragments) based on the request state.

```python
@app.get("/search")
async def search(request):
    results = await Post.search(request.query_params.get("q"))
    
    if request.headers.get("HX-Request"):
        # Returns ONLY the <ul> part of the template
        return request.render("search.html", {"results": results}, fragment="result-list")
        
    return request.render("search.html", {"results": results})
```

---

## Request & Response

### The `Request` object

Access headers, cookies, query Params, and body content.

```python
@app.get("/info")
async def info(request):
    ua = request.headers.get("user-agent")
    q = request.query_params.get("q")
    return {"ua": ua, "query": q}
```

### Response Helpers

Eden provides a range of response types.

```python
from eden import json, redirect, html

@app.get("/redirect")
async def do_redirect(request):
    return redirect(url="/")
```

---

## Advanced SaaS Routing Example 🏢

For enterprise applications, Eden supports sophisticated routing patterns using sub-domains and recursive middleware.

```python
from eden import Router

# Sub-domain routing for SaaS tenants
api_router = Router(prefix="/api/v1")
api_router.add_middleware("tenant")

@api_router.get("/metrics")
async def get_tenant_metrics(request):
    # request.state.tenant is populated by the middleware
    return {"tenant": request.state.tenant.id}

# Registering the router
app.include_router(api_router)
```

---

## 🏗️ Best Practices: Professional Namespacing

For large applications like a **School Management System**, namespacing is your best friend. It prevents name collisions and makes your code self-documenting.


### 1. The Multi-Level Pattern

Don't be afraid to nest namespaces.
 It makes your `@url` calls incredibly clear.

```python
# routes/admin/students.py
router = Router(name="students")

# routes/admin/__init__.py
admin_router = Router(name="admin")
admin_router.include_router(student_router, prefix="/students")

# app.py
app.include_router(admin_router, prefix="/admin")
```

Now, in your templates, you can call:
`@url('admin:students:list')`


### 2. Namespace vs. Prefix

- **Prefix**: The physical URL path (e.g., `/api/v1`).

- **Namespace**: The logical name used for code (e.g., `api`).
Always keep them synchronized for the easiest developer experience.



### 3. Use trailing slashes consistently

Eden handles trailing slashes automatically
, but for the best SEO and consistency, stick to the pattern defined in your `prefix`.

---

**Next Steps**: [Modern Templating Architecture](templating.md)
