# 🛡️ Middleware: High-Performance Request Pipeline

**Protect, audit, and transform your application traffic with Eden's integrated middleware architecture. By combining a "Fail-Secure" automatic stack with a low-latency priority system, Eden ensures your application is production-ready by default.**

---

## 🧠 Conceptual Overview

Middleware in Eden acts as a structured "onion" around your application logic. Every request travels through the layers from the outermost (Security) to the innermost (Authentication), and the response travels back out, allowing for transformation at every step.

### The Middleware Stack Architecture

```mermaid
graph TD
    A["Public Internet"] --> B["Middleware: Security Headers"]
    B --> C["Middleware: Session & CSRF"]
    C --> D["Middleware: Authentication"]
    D --> E["Middleware: Tenant Isolation"]
    E --> F["Route Handler: Business Logic"]
    F --> G["Response: JSON / HTML"]
    G --> H["Middleware: Transformation (GZip")]
    H --> I["Public Internet"]
```

---

## 🚀 The Automatic Middleware Stack

When you initialize an Eden application with a `secret_key`, the framework automatically registers a robust set of middleware to handle core SaaS concerns.

### 📋 Default Middleware Pipeline

| Priority | Name | Description |
| :--- | :--- | :--- |
| **-10** | `request_id` | Injects a unique `X-Request-ID` header and sets `request.id` for tracing. |
| **+10** | `security` | Transparently injects CSP, HSTS, and XSS protection headers. |
| **+20** | `session` | Provides encrypted, cookie-based session persistence. |
| **+30** | `csrf` | Protects your application from Cross-Site Request Forgery. |
| **+100** | `auth` | Populates `request.user` based on sessions or tokens. |
| **+500** | `cors` | Configures Cross-Origin Resource Sharing (Disabled by default). |
| **+1000** | `gzip` | Automatically compresses responses to save egress bandwidth. |

---

## 🏗️ Priority & Execution Order

Eden uses a relative priority system to determine the execution order, ensuring that critical security middleware always runs outside of general application logic.

```python
from eden import Eden

app = Eden()

# 1. Add with a custom priority (Lower values run FIRST)
class MyGuard:
    def __init__(self, app):
        self.app = app
    async def __call__(self, scope, receive, send):
        await self.app(scope, receive, send)

app.add_middleware(MyGuard, priority=app.PRIORITY_CORE + 5)

# 2. Add with pre-defined constants
# PRIORITY_CORE = 0
# PRIORITY_HIGH = 100
# PRIORITY_STANDARD = 500
# PRIORITY_LOW = 1000
```

---

## 🛡️ Built-in "Elite" Middleware

Eden comes pre-loaded with a suite of professional-grade middleware modules.

| Name | Elite Capability |
| :--- | :--- |
| `ratelimit` | In-memory token-bucket rate limiting per IP address. |
| `redis_ratelimit`| Distributed rate limiting across multiple server clusters. |
| `tenant` | **Fail-Secure** logic that scopes every query to the current tenant context. |
| `telemetry` | Injects `Server-Timing` headers and collects performance metrics. |
| `cache` | Smart caching for `GET` requests with automated cache-invalidation. |

---

## ⚡ Global vs Route-Specific Limiting

You can apply security protections globally or surgically for sensitive endpoints.

```python
from eden import Eden
from unittest.mock import MagicMock

app = Eden()
# Mock the limiter middleware for validation
def limiter(rate):
    return lambda f: f

# Global: 100 requests per minute across the entire app
app.add_middleware("ratelimit", rate="100/minute")

# Route-Specific: Only 5 login attempts per minute
@app.post("/api/login")
@limiter("5/minute")
async def login(request):
    return {"message": "Success"}
```

---

## 🎨 Creating Custom Middleware

Custom middleware allows you to intercept every request or response to inject custom logic (e.g., custom headers or logging).

```python
from eden import Eden
import time
from starlette.middleware.base import BaseHTTPMiddleware

app = Eden()

class HeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # 1. Before Logic: Tracing start
        start_time = time.time()
        
        # 2. Call the next layer
        response = await call_next(request)
        
        # 3. After Logic: Inject custom header
        response.headers["X-Process-Time"] = str(time.time() - start_time)
        return response

app.add_middleware(HeaderMiddleware)
```

---

## 💡 Best Practices

1.  **Lower Priority means Outer Layer**: Always keep security and tracing middleware at lower priority values (0-50).
2.  **Avoid Blocking in Middleware**: Never perform heavy computations or blocking I/O in the `dispatch` method. Offload these to background tasks.
3.  **Standardize Responses**: If you return an error from middleware (e.g., `403 Forbidden`), ensure you use `eden.json()` to maintain a consistent API schema.
4.  **Test Environment Isolation**: Eden automatically disables non-essential middleware (like CSRF) in the `test` environment to simplify unit testing.

---

**Next Steps**: [Dependency Injection & Resource Management](dependency-injection.md)
