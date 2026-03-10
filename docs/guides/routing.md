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

router = Router()

@router.get("/login")
async def login(request):
    ...
```

### `app.py`

```python
from routes.auth import router as auth_router

app.include_router(auth_router, prefix="/auth")
```

---

## Resource Routing (CRUD)

Eden's most powerful routing feature is the `Resource`. It automatically generates CRUD routes for a given model.

```python
from eden import Resource
from models import Post

class PostResource(Resource):
    model = Post
    
    # Custom Action
    @Resource.action(methods=["POST"])
    async def publish(self, request, pk):
        post = await self.get_object(pk)
        await post.update(status="published")
        return {"published": True}

app.add_resource(PostResource, prefix="/posts")
```

### Generated Resource Routes

By default, `add_resource` generates the following endpoints for your model:

| Method | Path | Action | Role |
| :--- | :--- | :--- | :--- |
| `GET` | `/posts` | `index` | List all records. |
| `POST` | `/posts` | `create` | Create a new record. |
| `GET` | `/posts/{id}` | `show` | View a single record. |
| `PUT` | `/posts/{id}` | `update` | Update a record. |
| `DELETE` | `/posts/{id}` | `destroy` | Delete a record. |

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
        return render_template("search.html", {"results": results}, fragment="result-list")
        
    return render_template("search.html", {"results": results})
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
from eden import JSONResponse, RedirectResponse, HTMLResponse

@app.get("/redirect")
async def do_redirect(request):
    return RedirectResponse(url="/")
```

---

## Advanced SaaS Routing Example 🏢

For enterprise applications, Eden supports sophisticated routing patterns using sub-domains and recursive middleware.

```python
from eden import Router
from eden.tenancy import tenant_middleware

# Sub-domain routing for SaaS tenants
api_router = Router(prefix="/api/v1")
api_router.add_middleware(tenant_middleware)

@api_router.get("/metrics")
async def get_tenant_metrics(request):
    # request.tenant is populated by the middleware
    return {"tenant": request.tenant.id}

# Registering the router
app.include_router(api_router)
```

**Next Steps**: [Modern Templating Architecture](templating.md)
