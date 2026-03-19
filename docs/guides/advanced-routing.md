# Advanced Routing with Metadata 🛣️

Eden routes support metadata (descriptions, tags, middleware) that enable automatic documentation, conditional logic, and organized route organization. This guide covers advanced routing patterns and metadata usage.

---

## Route Metadata Basics

### What is Metadata?

Every route can have:

```python
from eden import Router

router = Router()

@router.get(
    "/users/{id}",
    name="get_user",                    # Route name for URL building
    summary="Fetch user",               # Short description
    description="Get a specific user",  # Full documentation
    tags=["users"],                     # OpenAPI tags (grouping)
    middleware=[RequireAuth()],         # Route-specific middleware
    include_in_schema=True              # Include in OpenAPI schema
)
async def get_user(id: int, request):
    return {"id": id}
```

### When to Use Metadata

| Feature | Use Case |
|---------|----------|
| **name** | Route linking in templates: `url_for('get_user', id=123)` |
| **summary** | API documentation title |
| **description** | API documentation full text |
| **tags** | Group related routes in API docs |
| **middleware** | Route-specific auth, validation, logging |
| **include_in_schema** | Control which routes appear in API spec |

---

## Named Routes

### Create Named Routes

```python
from eden import Router

router = Router(prefix="/api/v1")

@router.get("/users/{id}", name="get_user")
async def get_user(id: int):
    return {"id": id}

@router.post("/users", name="create_user")
async def create_user(request):
    return {"created": True}

@router.delete("/users/{id}", name="delete_user")
async def delete_user(id: int):
    return {"deleted": True}
```

### Generate URLs from Names

**In route handlers:**

```python
from eden import Router
from eden.routing import url_for

router = Router()

@router.get("/users/{id}", name="get_user")
async def get_user(id: int, request):
    # Generate URL for related user
    delete_url = url_for(request, "delete_user", id=id)
    
    return {
        "id": id,
        "_links": {
            "delete": {"href": delete_url}
        }
    }
```

**In templates:**

```html
<!-- Generate links to named routes -->
<a href="@url_for('get_user', id=user.id)">View</a>
<a href="@url_for('delete_user', id=user.id)">Delete</a>
```

**In tests:**

```python
def test_user_links(client):
    response = client.get("/api/v1/users/123")
    
    links = response.json()["_links"]
    assert "/users/123" in links["delete"]["href"]
```

---

## Route Tags & Organization

### Tag Routes for GroupingAutomatically

```python
from eden import Router

router_users = Router(prefix="/api/users", tags=["users"])

@router_users.get("/{id}")
async def get_user(id: int):
    """Fetch a user."""
    return {"id": id}

@router_users.post("/")
async def create_user(request):
    """Create new user."""
    return {"created": True}

router_products = Router(prefix="/api/products", tags=["products"])

@router_products.get("/{id}")
async def get_product(id: int):
    """Fetch a product."""
    return {"id": id}

# Auto-generates tags:
# - /api/users/* routes tagged "users"
# - /api/products/* routes tagged "products"
```

### Override Tags per Route

```python
@router_users.get(
    "/search",
    tags=["search"]  # Override router's default tag
)
async def search_users(request):
    """Global user search - different tag."""
    return {}
```

### Tags in OpenAPI

```python
# Automatically generates API docs grouped by tag:
# Users
#   GET /api/users/{id}
#   POST /api/users
# Products
#   GET /api/products/{id}
#   POST /api/products
```

---

## Documentation Metadata

### Summaries & Descriptions

```python
@router.get(
    "/users/{id}",
    summary="Get user by ID",  # Short single-line summary
    description="""
    Retrieve a user by their ID.
    
    ## Responses
    - **200**: User found and returned
    - **404**: User not found
    - **401**: Unauthorized
    """
)
async def get_user(id: int):
    return {"id": id}
```

### Auto-Extract Documentation

If you don't provide summary/description, Eden uses the function docstring:

```python
@router.get("/users/{id}")
async def get_user(id: int):
    """
    Get a user by ID.
    
    This endpoint retrieves a specific user from the database.
    - User must exist or 404 is returned
    - No special permissions required
    """
    return {"id": id}

# Docstring automatically becomes description in OpenAPI
```

### Different Descriptions per Method

```python
@router.route(
    "/users",
    methods=["GET", "POST"],
    name="users",
    summary="User collection"
)
async def users(request):
    if request.method == "GET":
        return await list_users()
    else:
        return await create_user(request)

# Limit which methods appear in schema
@router.get(
    "/admin/stats",
    include_in_schema=False  # Hidden from OpenAPI docs
)
async def admin_stats():
    """Internal endpoint not meant for client consumption."""
    return {}
```

---

## Route-Specific Middleware

### Add Middleware to Single Route

```python
from eden import Router
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

class RequireAdminMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if not request.state.user or request.state.user.role != "admin":
            return JSONResponse({"error": "Admin required"}, 403)
        return await call_next(request)

router = Router(prefix="/api")

# This route has extra middleware
@router.get(
    "/stats",
    middleware=[RequireAdminMiddleware()]
)
async def admin_stats():
    return {"stats": {...}}

# Public route (no extra middleware)
@router.get("/data")
async def public_data():
    return {"data": {...}}
```

### Apply Middleware to Router

```python
router_admin = Router(
    prefix="/admin",
    tags=["admin"],
    middleware=[RequireAdminMiddleware()]  # All routes protected
)

@router_admin.get("/users")
async def list_users():
    """All admin routes automatically have middleware."""
    return {}

@router_admin.get("/reports")
async def reports():
    """Also protected."""
    return {}

# Add more middleware after creation
router_admin.add_middleware(LoggingMiddleware())
```

### Conditional Middleware

```python
class ConditionalAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Check if user authenticated
        if request.scope.get("user"):
            # Authenticated - proceed
            return await call_next(request)
        else:
            # Not authenticated - check if route allows it
            if request.scope.get("route_meta", {}).get("allow_anon"):
                return await call_next(request)
            else:
                return JSONResponse({"error": "Unauthorized"}, 401)

@router.get(
    "/public",
    middleware=[ConditionalAuthMiddleware()],
    allow_anon=True  # Custom metadata
)
async def public_route():
    return {}
```

---

## Advanced Pattern: Permission-Based Routes

### Role-Based Access Control

```python
class RBACMiddleware(BaseHTTPMiddleware):
    """Check that user has required role."""
    
    async def dispatch(self, request, call_next):
        required_roles = (
            request.scope.get("route_meta", {}).get("required_roles", [])
        )
        
        if not required_roles:
            return await call_next(request)
        
        user = request.scope.get("user")
        if not user:
            return JSONResponse({"error": "Unauthorized"}, 401)
        
        if user.role not in required_roles:
            return JSONResponse({"error": "Forbidden"}, 403)
        
        return await call_next(request)

# Usage
@router.get(
    "/admin/users",
    middleware=[RBACMiddleware()],
    required_roles=["admin"]
)
async def admin_users():
    """Only admins can access."""
    return {}

@router.get(
    "/user-list",
    middleware=[RBACMiddleware()],
    required_roles=["admin", "moderator"]
)
async def moderator_list():
    """Admins and moderators can access."""
    return {}
```

### Resource-Based Access Control (RBAC)

```python
class ResourceACLMiddleware(BaseHTTPMiddleware):
    """Check ownership of resource."""
    
    async def dispatch(self, request, call_next):
        resource_type = (
            request.scope.get("route_meta", {}).get("resource_type")
        )
        
        if not resource_type:
            return await call_next(request)
        
        # Extract ID from path
        path_params = request.scope.get("path_params", {})
        resource_id = path_params.get("id")
        
        if not resource_id:
            return JSONResponse({"error": "Invalid request"}, 400)
        
        # Check ownership
        user = request.scope.get("user")
        
        if resource_type == "post":
            post = await Post.get(resource_id)
            if post.user_id != user.id:
                return JSONResponse({"error": "Forbidden"}, 403)
        
        return await call_next(request)

@router.delete(
    "/posts/{id}",
    middleware=[ResourceACLMiddleware()],
    resource_type="post"
)
async def delete_post(id: int):
    """User can only delete their own posts."""
    return {"deleted": id}
```

---

## Advanced Pattern: Version Management

### API Versioning with Routers

```python
# v1: Legacy API
router_v1 = Router(
    prefix="/api/v1",
    tags=["v1"]
)

@router_v1.get("/users/{id}")
async def get_user_v1(id: int):
    """Original user endpoint."""
    return {"user_id": id, "version": 1}

# v2: Improved API
router_v2 = Router(
    prefix="/api/v2",
    tags=["v2"]
)

@router_v2.get("/users/{id}")
async def get_user_v2(id: int):
    """Improved user endpoint with more fields."""
    return {
        "id": id,
        "version": 2,
        "created_at": "2024-01-01",
        "updated_at": "2024-01-02"
    }

# v2 deprecated endpoint
@router_v2.get(
    "/old-endpoint",
    include_in_schema=False  # Hidden
)
async def deprecated():
    """Use /new-endpoint instead."""
    return {"error": "This endpoint is deprecated"}

app.include_router(router_v1)
app.include_router(router_v2)
```

---

## Advanced Pattern: Soft Deprecation

### Deprecation Warnings

```python
class DeprecationMiddleware(BaseHTTPMiddleware):
    """Add deprecation warning headers."""
    
    async def dispatch(self, request, call_next):
        deprecated = (
            request.scope.get("route_meta", {}).get("deprecated")
        )
        
        response = await call_next(request)
        
        if deprecated:
            response.headers["Deprecation"] = "true"
            response.headers["Sunset"] = deprecated.get("sunset_date")
            response.headers["Link"] = (
                f'<{deprecated.get("replacement")}>; rel="successor-version"'
            )
        
        return response

@router.get(
    "/users/{id}/profile",
    middleware=[DeprecationMiddleware()],
    deprecated={
        "sunset_date": "2024-12-31T00:00:00Z",
        "replacement": "/api/v2/users/{id}"
    }
)
async def get_profile(id: int):
    """
    DEPRECATED: Use /api/v2/users/{id} instead.
    
    This endpoint will be removed on 2024-12-31.
    """
    return {}
```

---

## Dynamic Route Generation

### Generate Routes Programmatically

```python
from eden.routing import Route

def create_crud_routes(model_name, model_class):
    """Generate CRUD routes for a model."""
    
    routes = []
    
    # List route
    async def list_items():
        items = await model_class.all()
        return {"items": [item.dict() for item in items]}
    
    routes.append(Route(
        path=f"/{model_name}",
        endpoint=list_items,
        methods=["GET"],
        name=f"list_{model_name}",
        summary=f"List {model_name}",
        tags=[model_name]
    ))
    
    # Detail route
    async def get_item(id: int):
        item = await model_class.get(id)
        return item.dict()
    
    routes.append(Route(
        path=f"/{model_name}/{{id}}",
        endpoint=get_item,
        methods=["GET"],
        name=f"get_{model_name}",
        summary=f"Get {model_name}",
        tags=[model_name]
    ))
    
    return routes

# Usage
for route in create_crud_routes("users", User):
    app.routes.append(route)

for route in create_crud_routes("posts", Post):
    app.routes.append(route)
```

---

## Inspecting Routes

### List All Routes with Metadata

```python
def print_routes(app):
    """Debug helper to print all routes."""
    for route in app.routes:
        print(f"{route.methods} {route.path}")
        print(f"  Name: {route.name}")
        print(f"  Summary: {route.summary}")
        print(f"  Tags: {route.tags}")
        print(f"  Middleware: {len(route.middleware)} middleware(s)")
        print()

# Useful for CLI or debug page
@app.get("/debug/routes")
async def debug_routes():
    routes = []
    for route in app.routes:
        routes.append({
            "method": route.methods,
            "path": route.path,
            "name": route.name,
            "tags": route.tags,
            "middleware": len(route.middleware)
        })
    return {"routes": routes}
```

---

## API Reference

### Route Parameters

```python
@router.route(
    path="/items/{id}",                    # URL path
    methods=["GET", "POST"],               # HTTP methods
    name="item_detail",                    # Route name
    summary="Get item details",            # Short description
    description="Full documentation...",    # Long description
    tags=["items"],                        # OpenAPI tags
    middleware=[auth_middleware],          # Extra middleware
    include_in_schema=True                 # Include in OpenAPI
)
```

### Router Configuration

```python
Router(
    prefix="/api/v1",                      # URL prefix
    name="api_v1",                         # Router name
    tags=["v1"],                           # Default tags
    middleware=[cors_middleware],          # Default middleware
    model=UserModel                        # Auto-generate CRUD
)
```

---

## Next Steps

- [Dependency Injection](../guides/dependency-injection.md) - Dynamic parameter resolution
- [OpenAPI Documentation](../guides/openapi.md) - Automatic API documentation
- [Security & Middleware](security.md) - Middleware patterns
- [URL Generation](../guides/templating.md) - url_for in templates
