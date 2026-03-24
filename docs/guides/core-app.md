# The Eden Engine ⚙️

The `Eden` class is the heart of your application. It manages routing, middleware, templating, and the overall application lifecycle.

## The App Object

Instantiating Eden is simple, but it comes with a variety of configuration options.

```python
from eden import Eden

app = Eden(
    title="My Eden Project",
    debug=True,
    description="A premium web application",
    version="1.0.0"
)

# Customize directories after initialization
app.template_dir = "theme/templates"
app.static_dir = "public"
```

### Configuration Options (Constructor)

| Option | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `title` | `str` | `"Eden"` | The display name of your application. |
| `version` | `str` | `"0.1.0"` | The version string for your application. |
| `debug` | `bool` | `False` | Enables the premium glassmorphic error page and auto-reload. |
| `description` | `str` | `""` | A brief description of the application. |
| `secret_key` | `str` | `""` | Used for session signing and security. |

### Configuration Precedence

Eden resolves configuration in the following order:

1.  **Explicit constructor arguments**: Values passed directly to the `Eden()` constructor.
2.  **Configuration object values**: Values from a standard `Config` object or environment variables.
3.  **Framework Defaults**: Sensible defaults provided by Eden.

> [!NOTE]
> The `debug` flag is special: a value of `True` explicitly passed to the constructor will always override any configuration or environment setting.

### Automatic Bootstrapping

Eden's `ServiceBootstrapper` automatically configures core services if it detects relevant settings in your app's state or environment:

-   **Database**: Automatic connection and table creation (for SQLite) if `app.state.database_url` is set.
-   **Cache**: Redis-backed cache is auto-configured if `REDIS_URL` is found in the environment.

### Instance Attributes

These properties can be customized after the `Eden` instance is created:

| Attribute | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `template_dir` | `str` | `"templates"` | The directory where your HTML files are stored. |
| `static_dir` | `str` | `"static"` | The directory for static assets. |
| `static_url` | `str` | `"/static"` | The URL prefix for serving static files. |
| `media_dir` | `str` | `"media"` | The directory for user-uploaded media. |

---

## Application Lifecycle

Eden provides "Lifecycle Hooks" that allow you to execute code at specific points in the application's existence.

### Startup Hooks

Ideal for connecting to databases, initializing caches, or pre-loading data.

```python
from eden import Eden
from unittest.mock import AsyncMock
app = Eden()
db = AsyncMock() # Mock database for example

@app.on_startup
async def setup_db():
    await db.connect()
    print("Database connected! ⚡")
```

### Shutdown Hooks

Ideal for clean-up tasks like closing database connections or stopping background workers.

```python
from eden import Eden
from unittest.mock import AsyncMock
app = Eden()
db = AsyncMock() # Mock database for example

@app.on_shutdown
async def close_db():
    await db.disconnect()
    print("Eden is resting. 🌿")
```

---

## Global State

You can attach objects to the `app` instance to make them accessible throughout your application.

```python
from eden import Eden
from unittest.mock import MagicMock
Cache = MagicMock

app = Eden()
app.cache = Cache()

# Access in a route
@app.get("/")
async def index(request):
    cache_status = app.cache.is_ready
    return {"status": cache_status}
```

---

## Application State (`app.state`)

The `app.state` object is a thread-safe storage for your application's global resources. It is the recommended place to store database pools, API clients, and other long-lived objects.

```python
from eden import Eden
from unittest.mock import MagicMock
StripeClient = MagicMock
app = Eden()

# Initialization (usually in app.py or a service provider)
app.state.stripe_client = StripeClient(api_key="sk_test_...")

# Usage in a route
@app.get("/checkout")
async def checkout(request):
    client = request.app.state.stripe_client
    # ... logic ...
    return {"status": "success"}
```

---


---

## Execution Philosophy: ASGI & Worker Flow

Eden follows the standard ASGI 3.0 specification. When a request arrives, it travels through the following sequence:

1. **Gatekeeper**: Middleware (Auth, CSRF, Security Headers).
2. **Navigator**: Router (Path & Method matching).
3. **Execution**: Your `async` handler.
4. **Resonance**: Response processing & Template rendering.

---


---

### Automatic Middleware Stack

When you specify a `secret_key` and aren't in a test environment, Eden automatically assembles a robust middleware stack in the following execution order:

1.  **Request ID**: Injects a unique `X-Request-ID` into every request.
2.  **Security**: Configures security headers (CSP, HSTS, XSS protection).
3.  **Session & CSRF**: (Conditional) Encrypted cookie sessions and CSRF protection.
4.  **Auth**: Provides `request.user` and authentication logic.
5.  **GZip**: Compresses compatible high-volume responses.
6.  **CORS**: Secure Cross-Origin Resource Sharing defaults.

---

**Next Steps**: [Advanced Routing](routing.md)
