# Eden Framework - Feature Activation & Integration Status

**Generated:** 2026-04-08  
**Status:** All features implemented and production-ready ✅

---

## Executive Summary

| Feature | Framework Status | App Integration | Config | Activation | Tests | Production Ready |
|---------|------------------|-----------------|--------|------------|-------|------------------|
| **HTMX** | ✅ Complete | ❌ Not in app/ | None | `from eden.htmx import HtmxResponse` | ✅ Passing | ✅ Yes |
| **WebSockets** | ✅ Complete | ❌ Not in app/ | None | `@app.websocket()` | ✅ Passing | ✅ Yes |
| **Background Tasks** | ✅ Complete | ❌ Not in app/ | Redis URL | `@app.task()` | ✅ Passing | ✅ Yes |
| **Stripe** | ✅ Complete | ❌ Not in app/ | API Key + Secret | `app.configure_payments()` | ✅ Passing | ✅ Yes |
| **Tenancy** | ✅ Complete | ❌ Not in app/ | Strategy + Domain | `app.add_middleware()` | ✅ Passing | ✅ Yes |

**Key Finding:** None of the features are demonstrated or enabled in the example app (`app/support_app.py`). Each requires explicit initialization code.

---

## 1. HTMX Integration

### Implementation Status
- **Location:** `eden/htmx.py` + `eden/templating/templates.py`
- **Status:** ✅ **Fully Implemented & Tested**

### Functionality
- ✅ **HtmxResponse Class** - Fluent API for setting HTMX headers
  - `.trigger()`, `.trigger_after_swap()`, `.trigger_after_settle()`
  - `.hx_redirect()`, `.refresh()`, `.swap()`, `.retarget()`, `.reselect()`, `.push_url()`
  
- ✅ **Smart Fragment Rendering** - Automatic template fragment resolution
  - Detects `HX-Target` header from HTMX requests
  - Renders only the requested fragment instead of full page
  - Fallback to full template if fragment not found
  
- ✅ **Request Helpers**
  - `is_htmx(request)` - Check if request from HTMX
  - `hx_target()`, `hx_trigger_id()`, `hx_trigger_name()`, `hx_current_url()`
  - `hx_vals()`, `hx_headers()` - Template filters for serialization

### How to Activate
```python
from eden.htmx import HtmxResponse, is_htmx

@app.get("/items")
async def get_items(request: Request):
    if is_htmx(request):
        # Respond with fragment if HTMX request
        html = render_fragment("items_list.html", context)
        return HtmxResponse(html).trigger("itemsLoaded")
    else:
        # Full page response
        return templates.TemplateResponse("items_list.html", context)
```

### Configuration
- **Environment Variables:** None
- **Code Configuration:** None required (works out-of-the-box)
- **Dependencies:** None (uses Starlette)

### Tests
- ✅ `tests/test_design_system.py::TestHtmxIntegration` - 8+ tests
- ✅ `tests/test_htmx_smart_fragments.py` - Fragment resolution tests
- **Status:** All passing

### Known Issues
- None documented

---

## 2. WebSockets

### Implementation Status
- **Location:** `eden/websocket/` package
  - `eden/websocket/manager.py` - ConnectionManager (500+ lines)
  - `eden/websocket/router.py` - WebSocketRouter (224 lines)
  - `eden/websocket/auth.py` - Authentication utilities
- **Status:** ✅ **Fully Implemented & Tested**

### Functionality
- ✅ **ConnectionManager** - Unified connection + pub/sub system
  - Channel/room-based broadcasting
  - Per-user connection tracking (`_user_sockets`)
  - Heartbeat ping/pong for dead connection detection
  - Distributed backend support (Redis)
  - Origin & CSRF security validation
  - Exponential backoff retry (5 retries, up to 32s)
  
- ✅ **WebSocketRouter** - Decorator-based event handling
  - `@ws.on(event_name)` - Event handler registration
  - `@ws.on_connect()`, `@ws.on_disconnect()` - Lifecycle hooks
  - Dynamic subscription/unsubscription at runtime
  - Built-in authorization checks for tenant/org isolation
  
- ✅ **Real-time Broadcasting**
  - Channel-based: `await manager.broadcast(message, channel="name")`
  - User-targeted: `await manager.send_to_user(user_id, message)`
  - Cross-worker distributed (Redis)
  - Dead connection cleanup
  
- ✅ **Security**
  - Origin validation (configurable allow list)
  - CSRF token verification via query params
  - User/tenant/org isolation enforcement
  - Superuser bypass for debugging

### How to Activate
```python
from eden.websocket import WebSocketRouter, connection_manager

ws = WebSocketRouter(prefix="/ws", auth_required=True)

@ws.on_connect
async def on_connect(socket, manager):
    await manager.broadcast({"user_joined": True}, channel="lobby")

@ws.on("message")
async def on_message(socket, data, manager):
    await manager.broadcast(data, channel="global", exclude=socket)

# Register routes
app.routes.extend(ws.routes)
```

### Configuration
- **Environment Variables:** None
- **Code Configuration:** 
  - Heartbeat interval (default 30s)
  - Auth required (default False)
  - CSRF validation (default False)
- **Dependencies:** Starlette (included), optional Redis for distributed

### Tests
- ✅ `tests/test_tier2_websocket.py` - 30+ comprehensive tests
- ✅ Tests cover: connection state, authentication, lifecycle, messaging, broadcasting
- **Status:** All passing

### Known Issues
- None documented

---

## 3. Background Tasks (with Redis)

### Implementation Status
- **Location:** `eden/tasks/` package
  - `eden/tasks/__init__.py` - EdenBroker (30KB)
  - `eden/tasks/scheduler.py` - TaskScheduler with cron
  - `eden/tasks/routes.py` - Task status API
- **Status:** ✅ **Fully Implemented & Tested**

### Functionality
- ✅ **Task Queue (Taskiq-based)**
  - Redis-backed with automatic InMemoryBroker fallback
  - Async task execution: `@app.task() async def my_task()`
  - Automatic dependency injection
  - Result tracking and persistence
  
- ✅ **Periodic/Scheduled Tasks**
  - Cron-style: `@app.schedule("0 12 * * *")`
  - Programmatic: `app.scheduler.schedule(func, "0 */6 * * *")`
  - Full cron syntax support with ranges, step values, lists
  
- ✅ **Error Recovery**
  - Exponential backoff: [1s, 2s, 4s, 8s, 16s]
  - Configurable max retries (default 3)
  - Dead-letter queue for failed tasks
  - Task result storage with TTL (7 days)
  
- ✅ **Task Status API**
  - `/api/eden/tasks/{task_id}/status` endpoint
  - Dual JSON/HTMX response support
  - Task progress component for UI

### How to Activate
```python
from eden import Eden

app = Eden(...)
app.setup_tasks()  # Auto-configures Redis or InMemoryBroker

@app.task()
async def send_email(to: str, subject: str):
    # Background task
    await send_email_service(to, subject)

@app.schedule("0 */6 * * *")  # Every 6 hours
async def cleanup_expired_tokens():
    await PasswordResetToken.delete_expired()

# Enqueue task
task_id = await send_email.kiq("user@example.com", "Hello")
```

### Configuration
- **Environment Variables:**
  - `REDIS_URL=redis://localhost:6379` (optional)
  - Falls back to InMemoryBroker if not set
  
- **Code Configuration:**
  - Call `app.setup_tasks()` during app initialization
  - Configure max retries, retry delays via broker config
  
- **Dependencies:**
  - `taskiq` - Core task queue (required)
  - `taskiq_redis` - Redis broker (auto-detected)
  - `croniter` - Cron parsing (optional)

### Tests
- ✅ `tests/test_tasks.py` - Basic task registration
- ✅ `tests/test_tasks_full.py` - Full integration tests
- ✅ `tests/test_tasks_comprehensive.py` - Comprehensive coverage
- ✅ `tests/test_task_result_backend.py` - Result storage
- ✅ `tests/test_background_tasks.py` - App integration
- **Status:** All passing

### Redis Fallback
- ✅ **Working** - If `REDIS_URL` not set or connection fails
- Broker type: `InMemoryBroker` (in-process, doesn't survive restarts)
- Diagnostic warning: `app._diagnostics.register(..., "degraded", "Using in-memory task queue")`

### Known Issues
- None documented

---

## 4. Stripe Integration

### Implementation Status
- **Location:** `eden/payments/` package
  - `eden/payments/providers.py` - StripeProvider (178 lines)
  - `eden/payments/webhooks.py` - WebhookRouter (150 lines)
  - `eden/payments/models.py` - Customer, Subscription, PaymentEvent
- **Status:** ✅ **Fully Implemented & Tested**

### Functionality
- ✅ **StripeProvider Implementation**
  - Async API wrapper using `asyncio.to_thread()`
  - Uses `stripe.StripeClient` (not global state) - multi-tenant safe
  - API version pinned: `"2024-12-18.acacia"`
  - Methods:
    - `create_customer(email, name, metadata)` → customer_id
    - `create_checkout_session(...)` → checkout_url
    - `create_portal_session(...)` → portal_url
    - `cancel_subscription(subscription_id)` → bool
    - `get_subscription(subscription_id)` → dict
    - `verify_webhook_signature(payload, signature)` → event dict
    
- ✅ **Webhook Routing**
  - `@webhooks.on("event.type")` - Event handler registration
  - Multi-handler support per event
  - Signature verification + idempotency via `PaymentEvent`
  
- ✅ **Database Models**
  - `Customer` - Links user to Stripe customer
  - `Subscription` - Tracks subscription status, period end
  - `PaymentEvent` - Raw webhook events for audit + idempotency
  
- ✅ **BillableMixin** (used on User model)
  - `stripe_customer_id` field (indexed)
  - `billing` property → BillingManager instance
  - `is_subscribed()` - Check active subscription
  - `billing.create_checkout_session(plan_id, ...)`
  - `billing.create_portal_session(return_url)`

### How to Activate
```python
from eden.payments import StripeProvider
from eden import Eden

app = Eden(title="SaaS")

# Configure Stripe
provider = StripeProvider(
    api_key="sk_live_...",
    webhook_secret="whsec_...",
)
app.configure_payments(provider)

# In routes
@app.post("/checkout")
async def checkout(request: Request):
    checkout_url = await request.user.billing.create_checkout_session(
        plan_id="price_...",
        success_url=request.url_for("success"),
        cancel_url=request.url_for("pricing"),
    )
    return {"url": checkout_url}

# Webhooks (manual setup required)
@app.post("/webhooks/stripe")
async def stripe_webhook(request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    event = app.payments.verify_webhook_signature(payload, sig_header)
    # Handle event...
```

### Configuration
- **Environment Variables:**
  - `STRIPE_API_KEY=sk_test_...`
  - `STRIPE_WEBHOOK_SECRET=whsec_...`
  - **Note:** Must be manually read and passed to StripeProvider (not auto-loaded)
  
- **Code Configuration:**
  - `app.configure_payments(StripeProvider(...))`
  - Webhook route registration (manual)
  
- **Dependencies:**
  - `stripe` >= 14.4.0 (optional, install with `uv add stripe`)

### Tests
- ✅ `tests/test_config_and_testing.py` - Config loading
- ✅ `tests/test_documentation_examples.py::test_stripe_webhook_verification` - Webhook
- ✅ Mock Stripe available in `tests/conftest.py`
- **Status:** Tests passing

### Known Issues
- ❌ **Webhook route is NOT auto-registered** - Requires manual setup
- ⚠️ Environment variables NOT auto-loaded - Must pass explicitly to StripeProvider

---

## 5. Tenancy (Multi-Tenant)

### Implementation Status
- **Location:** `eden/tenancy/` package
  - `eden/tenancy/middleware.py` - TenantMiddleware (resolver strategies)
  - `eden/tenancy/models.py` - Tenant model + lifecycle
  - `eden/tenancy/mixins.py` - TenantMixin for query filtering
  - `eden/tenancy/context.py` - ContextVar storage
- **Status:** ✅ **Fully Implemented & Tested**

### Functionality
- ✅ **Tenant Resolution Strategies**
  - `"subdomain"` - Extract from subdomain (acme.example.com → "acme")
  - `"header"` - Read from custom header (X-Tenant-ID)
  - `"session"` - Read from session key
  - `"path"` - Extract from URL prefix (/t/acme/...)
  
- ✅ **Tenant Model**
  - Fields: name, slug (unique), is_active, plan_id, schema_name
  - Signals: tenant_created, tenant_deactivated, tenant_deleted, tenant_schema_provisioned
  - Methods: `provision_schema()` - Dynamic PostgreSQL schema creation
  
- ✅ **TenantMixin** (for models)
  - Automatic `tenant_id` filtering in queries
  - Prevents data leakage across tenants
  - Works with `.filter()` and `.all()`
  
- ✅ **Multi-Schema Support**
  - Dedicated PostgreSQL schema per tenant
  - `provision_schema()` creates schema + tables automatically
  - Alembic integration for migration stamping
  
- ✅ **Security**
  - Fail-secure enforcement (rejects without valid tenant by default)
  - Default exempt paths: /health, /ready, /metrics, /static, /api/eden/, /_eden/
  - User/tenant/org isolation validation
  - ContextVar for async safety

### How to Activate
```python
from eden import Eden
from eden.tenancy import TenantMixin
from eden.db import Model, Field as f

app = Eden(title="SaaS", debug=True)

# Register tenant middleware - choose ONE strategy
app.add_middleware("tenant", strategy="subdomain", base_domain="myapp.com")
# OR:
# app.add_middleware("tenant", strategy="header", header_name="X-Tenant-ID")
# OR:
# app.add_middleware("tenant", strategy="path")

# Use TenantMixin on app-specific models
class Project(Model, TenantMixin):
    __tablename__ = "projects"
    name: str = f(max_length=200)
    # tenant_id is automatically added + filtered

# In routes - tenant is auto-resolved
@app.post("/projects")
async def create_project(request: Request):
    tenant = request.tenant  # Resolved by middleware
    project = await Project.create(
        name="My Project",
        tenant_id=tenant.id  # Automatic isolation
    )
    return {"id": project.id}

# Query auto-filtered by current tenant
projects = await Project.all()  # Only for current tenant
```

### Configuration
- **Environment Variables:** None
- **Code Configuration:**
  - `app.add_middleware("tenant", strategy=..., ...)`
  - Strategy: subdomain, header, session, or path
  - Base domain (for subdomain strategy)
  - Enforcement mode (default: True - fail-closed)
  - Exempt paths (default: standard set)
  
- **Dependencies:** None (built-in)

### Tenant Context Management
```python
from eden.tenancy import (
    set_current_tenant,
    get_current_tenant,
    get_current_tenant_id,
    reset_current_tenant,
)

# Manual context control
set_current_tenant(tenant_id)
current_tenant = get_current_tenant()
# Queries now auto-filtered by this tenant
```

### Tests
- ✅ `tests/test_tenant_middleware.py` - Middleware enforcement
- ✅ `tests/test_multitenant_security.py` - Security isolation
- ✅ `tests/test_migration_tenants.py` - Schema provisioning
- ✅ `tests/test_tenant_task_wrapper.py` - Background task isolation
- **Status:** All passing

### Comparison with django-tenants
| Aspect | Eden | django-tenants |
|--------|------|-----------------|
| **Design** | Async-first | Django ORM-centric |
| **ORM** | SQLAlchemy | Django ORM |
| **Isolation** | ContextVar + query filtering | Cursor routing workaround |
| **Multi-schema** | ✅ Yes | ✅ Yes |
| **Multi-database** | ✅ Yes | Limited |
| **Modern Framework** | ✅ Starlette/FastAPI | Django only |
| **Security** | Fail-secure (default enforce=True) | Developer configurable |

### Known Issues
- None documented

---

## Integration Checklist

### Example App (`app/support_app.py`)
- ❌ HTMX - Not integrated
- ❌ WebSockets - Not integrated
- ❌ Background Tasks - Not integrated
- ❌ Stripe - Not integrated
- ❌ Tenancy - Not integrated

### Why Not Integrated in Example App?
The example app is minimal and intentionally focuses on demonstrating basic CRUD operations. Features are opt-in to keep it simple.

### Recommended Next Steps to Enable in Example App

**1. Enable HTMX**
```python
# app/routes/items.py
from eden.htmx import HtmxResponse

@items_router.get("/items", name="list-items")
async def list_items(request: Request):
    items = await Item.all()
    if is_htmx(request):
        return HtmxResponse(
            render_fragment("items/list.html", {"items": items})
        )
    return templates.TemplateResponse("items/list.html", {"items": items})
```

**2. Enable WebSockets**
```python
# app/websockets.py
from eden.websocket import WebSocketRouter

ws = WebSocketRouter(prefix="/ws", auth_required=True)

@ws.on("message")
async def handle_message(socket, data, manager):
    await manager.broadcast(data, channel="chat")
```

**3. Enable Background Tasks**
```python
# app/tasks.py
@app.task()
async def send_notification(user_id: str, message: str):
    user = await User.get(user_id)
    await notify_service.send(user.email, message)

# app/routes/notifications.py
await send_notification.kiq(user_id, "New order placed!")
```

**4. Enable Stripe**
```python
# app/__init__.py
from eden.payments import StripeProvider

app = Eden(...)
app.configure_payments(StripeProvider(
    api_key=os.getenv("STRIPE_API_KEY"),
    webhook_secret=os.getenv("STRIPE_WEBHOOK_SECRET"),
))
```

**5. Enable Tenancy**
```python
# app/__init__.py
app.add_middleware("tenant", strategy="subdomain", base_domain="localhost")

# app/models.py
from eden.tenancy import TenantMixin

class Organization(Model, TenantMixin):
    name: str
    slug: str
```

---

## Summary

✅ **All 5 features are production-ready**  
❌ **None are enabled in example app (by design)**  
✅ **All have comprehensive test coverage**  
✅ **Smart fragment rendering works automatically**  
✅ **Redis fallback works for background tasks**  
✅ **Multi-tenant isolation is fail-secure**  

**To activate any feature:**
1. Add configuration code (environment variables, middleware, decorators)
2. Add activation in app initialization
3. Use the feature in routes/models

No modifications to Eden framework code are needed. All features are production-ready as-is.
