# Middleware 🛡️

Middleware allows you to wrap your application or specific routes with additional logic. This is where security, logging, and session management live.

## Adding Middleware

You can add middleware to your Eden instance globally using `add_middleware()`.

```python
from eden import Eden

app = Eden()

# Add by name (Built-in)
app.add_middleware("security")

app.add_middleware("gzip")

# Add by class
from my_app.middleware import CustomMiddleware
app.add_middleware(CustomMiddleware, some_config="value")
```

---

## Built-in Middleware

Eden comes pre-configured with a suite of high-performance middleware.

| Name | Description |
| :--- | :--- |
| `security` | Injects CSP, HSTS, and XSS protection headers. |
| `csrf` | Protects your app from Cross-Site Request Forgery. |
| `ratelimit` | Prevents abuse by limiting requests per IP. |
| `cors` | Configures Cross-Origin Resource Sharing. |
| `session` | Provides secure, cookie-based session persistence. |
| `gzip` | Compresses responses to save bandwidth. |
| `tenancy` | Scopes database queries to the current tenant. |

---

## Rate Limiting 🚦

Eden provides granular rate limiting via the `ratelimit` middleware and the `@limiter` decorator.

```python
# Enable globally
app.add_middleware("ratelimit", requests_per_minute=60)

# Override for specific routes
@app.get("/api/login")
@limiter("5/minute")
async def login(request):
    ...
```

---

## CORS Configuration 🌐

Configure allowed origins, methods, and headers for your API.

```python
app.add_middleware(
    "cors",
    allow_origins=["https://example.com"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    allow_credentials=True
)
```

---

## Creating Custom Middleware

Custom middleware should inherit from the standard Starlette `BaseHTTPMiddleware` (or use a compatible ASGI pattern).

```python
from starlette.middleware.base import BaseHTTPMiddleware

class HeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Eden-App"] = "True"
        return response

app.add_middleware(HeaderMiddleware)
```

---

## Middleware Ordering

Ordering is critical. Middleware is executed in a "last-in, first-out" (LIFO) order for the request (the last one added is the first one to receive the request) and FIFO for the response.

**General recommendation**:

1. Global Error Handling
2. GZip
3. Security Headers
4. Authentication
5. Session

---

**Next Steps**: [Internationalization & Multi-Tenancy](i18n.md)
