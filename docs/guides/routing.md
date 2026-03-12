# Routing System 🛣️

Eden's routing system is designed to be expressive, hierarchical, and type-safe.

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

---

## Sub-Routers

As your application grows, you can split your routes into separate modules using the `Router` class.

### `routes/auth.py`

```python
from eden import Router

# Give the router a namespace name
router = Router(name="auth")

@router.get("/login", name="login")
async def login(request):
    ...
```

### `app.py`

```python
# Root-level app.py
from routes.auth import router as auth_router

app.include_router(auth_router, prefix="/auth")
```

When you include a named router, all its route names are automatically prefixed with the namespace (e.g., `auth:login`). This is incredibly useful for reverse URL generation.

### Template URL Generation

Instead of hardcoding URLs, use the `@url` template directive or `request.url_for()` to dynamically generate paths based on route names.

```html
<!-- Inside a Jinja Template -->
<a href="@url('auth:login')">Sign In</a>

<!-- With dynamic parameters -->
<a href="@url('users:profile', id=user.id)">View Profile</a>
```

You can also generate URLs in your handlers:

```python
@app.get("/redirect")
async def go_login(request):
    return redirect(request.url_for("auth:login"))
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
