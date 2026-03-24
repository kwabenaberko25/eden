# API Versioning Guide 🛰️

Managing multiple versions of your API is essential for evolving your application without breaking existing clients. Eden provides a robust versioning system that supports multiple negotiation strategies (URL paths, headers) and automatic request/response transformations.

---

## Mental Model: How Versioning Works

Eden's versioning system follows these priorities when determining which version to use for a request:

Eden's versioning system follows these priorities when determining which version to use for a request:

1. **URL Path**: e.g., `/v2/users/123` (highest priority)
2. **API-Version Header**: e.g., `API-Version: v2`
3. **Accept-Version Header**: e.g., `Accept-Version: v2`
4. **Default Version**: Defined in your app configuration (lowest priority)

---

## Foundational: Setup

### 1. Register API Versions
Define your available versions and their properties in your main app entry point.

```python
from eden import Eden, APIVersion

app = Eden(__name__)

# Register versions
app.register_api_version(APIVersion("v1", default=True))
app.register_api_version(APIVersion("v2", deprecated=True, sunset_date="2025-12-31"))
```

### 2. Enable Versioning Middleware
Add the `VersionedMiddleware` to handle version negotiation automatically.

```python
from eden.versioning import VersionedMiddleware

# The middleware handles headers and populates scope['api_version']
app.add_middleware(VersionedMiddleware)
```

---

## Integration: Versioned Routing

Use the `VersionedRouter` to define version-specific endpoints for the same path.

```python
from eden.versioning import VersionedRouter
from eden.responses import JsonResponse

router = VersionedRouter()

# V1 Endpoint
@router.get("/profile", versions=["v1"])
async def get_profile_v1(request):
    return JsonResponse({"id": 1, "username": "alice"})

# V2 Endpoint (same URL, different structure)
@router.get("/profile", versions=["v2"])
async def get_profile_v2(request):
    return JsonResponse({
        "data": {"id": 1, "username": "alice", "email": "alice@eden.py"},
        "meta": {"version": "v2"}
    })

# Mount to the main app
router.mount(app, prefix="/api")
```

---

## Scalability: Request/Response Transformations

Instead of duplicating logic for every version, use **Version Transformers** to convert data between formats dynamically.

```python
class UserTransformer:
    async def v1_to_v2(self, data: dict):
        """Convert v1 User object to v2 format."""
        return {
            "id": data["id"],
            "username": data["username"],
            "email": "unknown@eden.py",  # v2 requires email
        }

# Register the transformer
app.set_version_transformer("User", UserTransformer())
```

---

## Visualizing the Flow

```mermaid
graph TD
    A[Incoming Request /v1/users] --> B{VersionedMiddleware}
    B -- Negotation Path --> C[Extract "v1" from URL]
    C --> D[Store v1 in scope['api_version']]
    D --> E[VersionedRouter Shim]
    E -- Match Handler --> F[get_users_v1]
    F --> G[Outgoing Response]
    G -- Wrap Send --> H[Add Header: x-api-version: v1]
    H --> I[Add Deprecation Headers if needed]
```

---

## Deprecation & Sunsetting

When a version is marked as `deprecated`, Eden automatically attaches standard HTTP headers to alert clients:

- `Deprecation: true`
- `Warning: 299 - "This API version is deprecated"`
- `Sunset: Sunday, 31 Dec 2025 00:00:00 GMT`

> [!WARNING]
> **Versioning Strategy**
> **Never remove** an API version without a clear sunset period. Always use the `sunset_date` feature to give your clients time to upgrade.

---

## Related Guides

- [Advanced Routing](advanced-routing.md)
- [Middleware](middleware.md)
- [Request & Response](requests-responses.md)
