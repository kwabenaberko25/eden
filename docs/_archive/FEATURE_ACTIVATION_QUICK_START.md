# Quick Start - Feature Activation Code

Copy-paste activation code for each feature in Eden Framework.

---

## 1. HTMX Integration

### Basic Setup
```python
from eden.htmx import HtmxResponse, is_htmx, hx_target
from eden.templating.templates import render_fragment

@app.get("/items")
async def list_items(request: Request):
    items = await Item.all()
    
    if is_htmx(request):
        # Return fragment only for HTMX requests
        html = render_fragment("items.html", {
            "items": items,
            "__fragment__": hx_target(request)  # Override fragment name
        })
        return HtmxResponse(html).trigger("itemsLoaded", {"count": len(items)})
    
    # Full page for normal requests
    return templates.TemplateResponse("items.html", {"items": items})
```

### Using in Templates
```html
<!-- items.html -->
<div id="items-list" hx-get="/items" hx-swap="innerHTML">
    {% if items %}
        {% for item in items %}
            <div class="item">{{ item.name }}</div>
        {% endfor %}
    {% else %}
        <p>No items found</p>
    {% endif %}
</div>
```

### Features Used
- ✅ Smart fragment rendering (`render_fragment`)
- ✅ Header detection (`is_htmx`, `hx_target`)
- ✅ HTMX response with triggers (`HtmxResponse.trigger`)

---

## 2. WebSockets

### Basic Setup
```python
from eden.websocket import WebSocketRouter, connection_manager

# Create router
ws = WebSocketRouter(
    prefix="/ws",
    auth_required=True,  # Require authentication
    heartbeat_interval=30  # Seconds
)

# Connection lifecycle
@ws.on_connect
async def on_connect(socket, manager: connection_manager):
    user_id = socket.user.id
    await manager.subscribe(f"user:{user_id}:messages", socket)
    await manager.broadcast({
        "type": "user.joined",
        "user_id": user_id
    }, channel=f"user:{user_id}:status")
    print(f"User {user_id} connected")

@ws.on_disconnect
async def on_disconnect(socket, manager):
    user_id = socket.user.id
    await manager.unsubscribe(f"user:{user_id}:messages", socket)
    print(f"User {user_id} disconnected")

# Message handlers
@ws.on("message")
async def on_message(socket, data: dict, manager):
    # Broadcast to channel
    await manager.broadcast(
        {"type": "message", "text": data.get("text")},
        channel="global",
        exclude=socket  # Don't send back to sender
    )

@ws.on("notification")
async def on_notification(socket, data: dict, manager):
    # Send to specific user
    recipient_id = data.get("to")
    await manager.send_to_user(recipient_id, {
        "type": "notification",
        "from": socket.user.id,
        "text": data.get("text")
    })

# Register routes
app.routes.extend(ws.routes)
```

### Client-side (JavaScript)
```javascript
const ws = new WebSocket("ws://localhost:8000/ws?token=user-token");

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log("Message:", data);
};

ws.send(JSON.stringify({
    type: "message",
    text: "Hello, world!"
}));
```

### Features Used
- ✅ Connection lifecycle hooks (`@ws.on_connect`, `@ws.on_disconnect`)
- ✅ Event-based handlers (`@ws.on("event")`)
- ✅ Pub/sub broadcasting (`manager.broadcast`)
- ✅ User-targeted messaging (`manager.send_to_user`)
- ✅ Authentication required

---

## 3. Background Tasks

### Basic Setup
```python
from eden import Eden

app = Eden(title="MyApp", debug=True)

# Initialize task queue (Redis or InMemory fallback)
app.setup_tasks()

# Define one-shot task
@app.task()
async def send_email(recipient: str, subject: str, body: str):
    # This runs in background
    async with aiosmtplib.SMTP(hostname="localhost") as smtp:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = "noreply@example.com"
        message["To"] = recipient
        message.set_content(body)
        await smtp.send_message(message)

# Define periodic task (every 6 hours)
@app.schedule("0 */6 * * *")
async def cleanup_expired_sessions():
    # Delete sessions older than 7 days
    await Session.delete_many({
        "created_at": {"$lt": datetime.now() - timedelta(days=7)}
    })

# Define periodic task (every day at midnight)
@app.schedule("0 0 * * *")
async def generate_daily_report():
    report = await generate_report()
    await send_email("admin@example.com", "Daily Report", report)

# In routes - enqueue a task
@app.post("/contact")
async def contact_form(request: Request, data: dict):
    # Enqueue email (non-blocking)
    task_id = await send_email.kiq(
        recipient=data["email"],
        subject="Thank you for contacting us",
        body="We'll get back to you soon!"
    )
    
    return {
        "status": "queued",
        "task_id": task_id
    }

# Check task status
@app.get("/task/{task_id}/status")
async def task_status(task_id: str):
    result = await app.broker.task_result_backend.get_result(task_id)
    if result:
        return {
            "status": result.status,  # pending, running, success, failed
            "progress": result.progress,
            "result": result.result,
            "error": result.error
        }
    return {"error": "Task not found"}
```

### Configuration
```env
# .env
REDIS_URL=redis://localhost:6379

# If not set, uses InMemoryBroker (doesn't survive restarts)
```

### Features Used
- ✅ Background task execution (`@app.task()`)
- ✅ Cron scheduling (`@app.schedule(cron_expression)`)
- ✅ Task status tracking
- ✅ Automatic Redis connection (with InMemory fallback)

---

## 4. Stripe Integration

### Basic Setup
```python
import os
from eden import Eden
from eden.payments import StripeProvider

app = Eden(title="SaaS", debug=True)

# Configure Stripe provider
stripe_provider = StripeProvider(
    api_key=os.getenv("STRIPE_API_KEY"),
    webhook_secret=os.getenv("STRIPE_WEBHOOK_SECRET"),
    api_version="2024-12-18.acacia"
)
app.configure_payments(stripe_provider)

# Checkout endpoint
@app.post("/checkout")
async def create_checkout(request: Request, data: dict):
    user = request.user
    plan_id = data.get("plan_id")  # e.g., "price_..."
    
    # Create or get Stripe customer
    if not user.stripe_customer_id:
        customer_id = await app.payments.create_customer(
            email=user.email,
            name=user.name,
            metadata={"user_id": user.id}
        )
        user.stripe_customer_id = customer_id
        await user.save()
    
    # Create checkout session
    checkout_url = await app.payments.create_checkout_session(
        customer_id=user.stripe_customer_id,
        price_id=plan_id,
        success_url=request.url_for("checkout_success"),
        cancel_url=request.url_for("pricing"),
        mode="subscription"
    )
    
    return {"checkout_url": checkout_url}

# Billing portal
@app.get("/billing")
async def billing_portal(request: Request):
    user = request.user
    
    portal_url = await app.payments.create_portal_session(
        customer_id=user.stripe_customer_id,
        return_url=request.url_for("dashboard")
    )
    
    return {"redirect_url": portal_url}

# Webhook handler
@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = app.payments.verify_webhook_signature(payload, sig_header)
    except Exception as e:
        return {"error": str(e)}, 400
    
    # Handle different event types
    if event["type"] == "customer.subscription.updated":
        subscription_data = event["data"]["object"]
        customer_id = subscription_data["customer"]
        
        # Update database
        from eden.payments.models import Subscription
        await Subscription.update_or_create(
            provider_subscription_id=subscription_data["id"],
            defaults={
                "status": subscription_data["status"],
                "current_period_end": subscription_data["current_period_end"],
                "cancel_at_period_end": subscription_data["cancel_at_period_end"]
            }
        )
    
    elif event["type"] == "customer.subscription.deleted":
        subscription_data = event["data"]["object"]
        # Handle cancellation
    
    return {"status": "ok"}

# Check subscription status
@app.get("/subscription/status")
async def check_subscription(request: Request):
    user = request.user
    is_subscribed = await user.is_subscribed()
    
    return {
        "is_subscribed": is_subscribed,
        "can_access_premium": is_subscribed
    }
```

### Environment Variables
```env
STRIPE_API_KEY=sk_test_... (or sk_live_...)
STRIPE_WEBHOOK_SECRET=whsec_...
```

### Features Used
- ✅ Stripe provider initialization
- ✅ Customer creation
- ✅ Checkout session creation
- ✅ Billing portal
- ✅ Webhook signature verification
- ✅ Subscription tracking

---

## 5. Tenancy (Multi-Tenant)

### Basic Setup with Subdomain Strategy
```python
from eden import Eden
from eden.tenancy import TenantMixin
from eden.db import Model, Field as f

app = Eden(title="SaaS", debug=True)

# Enable multi-tenancy with subdomain strategy
app.add_middleware(
    "tenant",
    strategy="subdomain",
    base_domain="example.com",  # Requests to acme.example.com → tenant "acme"
    enforce=True,  # Reject requests without valid tenant (fail-secure)
    exempt_paths=["/health", "/ready", "/api/auth", "/static"]
)

# Models with automatic tenant isolation
class Project(Model, TenantMixin):
    __tablename__ = "projects"
    name: str = f(max_length=200)
    description: str = f(nullable=True)
    # tenant_id is automatically added by TenantMixin

class Task(Model, TenantMixin):
    __tablename__ = "tasks"
    title: str = f(max_length=100)
    project_id: str = f(foreign_key="projects.id")
    # tenant_id is automatically added by TenantMixin

# Routes - tenant is auto-resolved from request
@app.get("/projects")
async def list_projects(request: Request):
    # Queries are automatically filtered by tenant_id
    projects = await Project.all()
    return {"projects": [p.dict() for p in projects]}

@app.post("/projects")
async def create_project(request: Request, data: dict):
    tenant = request.tenant  # Auto-resolved by middleware
    
    project = await Project.create(
        name=data["name"],
        description=data.get("description"),
        tenant_id=tenant.id  # Explicit for clarity (auto-filtered on query)
    )
    return {"id": project.id}

@app.get("/projects/{project_id}/tasks")
async def list_tasks(request: Request, project_id: str):
    # Tasks automatically filtered by both project_id AND tenant_id
    tasks = await Task.filter(project_id=project_id).all()
    return {"tasks": [t.dict() for t in tasks]}
```

### Alternative: Header Strategy
```python
app.add_middleware(
    "tenant",
    strategy="header",
    header_name="X-Tenant-ID"  # Client sends: X-Tenant-ID: acme
)
```

### Alternative: Path Strategy
```python
app.add_middleware(
    "tenant",
    strategy="path"  # Requests to /t/acme/projects → tenant "acme"
)

# Routes would be:
# @app.get("/t/{tenant_slug}/projects")
# The tenant_slug is extracted and resolved automatically
```

### Manual Tenant Context (for background tasks)
```python
from eden.tenancy import set_current_tenant, get_current_tenant_id

@app.task()
async def send_tenant_report(tenant_id: str):
    # Set tenant context for background task
    set_current_tenant(tenant_id)
    
    try:
        # All queries now filtered by tenant_id
        projects = await Project.all()
        total_tasks = len(projects)
        
        # Send report
        await send_email(
            to="admin@example.com",
            subject=f"Report for tenant {tenant_id}",
            body=f"Total projects: {total_tasks}"
        )
    finally:
        reset_current_tenant()
```

### Features Used
- ✅ TenantMiddleware with multiple strategies
- ✅ TenantMixin for automatic query filtering
- ✅ Tenant context resolution
- ✅ Multi-schema support (with PostgreSQL)
- ✅ Fail-secure enforcement

---

## Full App Example

```python
import os
from eden import Eden
from eden.htmx import HtmxResponse, is_htmx
from eden.websocket import WebSocketRouter
from eden.payments import StripeProvider
from eden.tenancy import TenantMixin
from eden.db import Model, Field as f

# Initialize app
app = Eden(
    title="SaaS Platform",
    debug=os.getenv("DEBUG", "false").lower() == "true"
)

# === TENANCY ===
app.add_middleware("tenant", strategy="subdomain", base_domain="example.com")

# === BACKGROUND TASKS ===
app.setup_tasks()

@app.task()
async def send_notification_email(user_id: str, message: str):
    user = await User.get(user_id)
    # Send email...

@app.schedule("0 0 * * *")  # Daily
async def cleanup_expired_tokens():
    await PasswordResetToken.delete_expired()

# === STRIPE ===
app.configure_payments(StripeProvider(
    api_key=os.getenv("STRIPE_API_KEY"),
    webhook_secret=os.getenv("STRIPE_WEBHOOK_SECRET"),
))

# === WEBSOCKETS ===
ws = WebSocketRouter(prefix="/ws", auth_required=True)

@ws.on("chat")
async def on_chat(socket, data, manager):
    await manager.broadcast(
        {"type": "chat", "message": data["text"]},
        channel="global"
    )

app.routes.extend(ws.routes)

# === MODELS ===
class User(Model, TenantMixin):
    email: str = f(max_length=255)
    name: str = f(max_length=100)
    stripe_customer_id: str = f(nullable=True)

class Project(Model, TenantMixin):
    name: str = f(max_length=200)
    owner_id: str = f(foreign_key="users.id")

# === ROUTES ===
@app.get("/dashboard")
async def dashboard(request: Request):
    projects = await Project.all()
    
    if is_htmx(request):
        html = render_fragment("projects_list.html", {"projects": projects})
        return HtmxResponse(html).trigger("loaded")
    
    return templates.TemplateResponse("dashboard.html", {"projects": projects})

@app.post("/checkout")
async def checkout(request: Request):
    checkout_url = await request.user.billing.create_checkout_session(
        plan_id="price_...",
        success_url=request.url_for("success"),
        cancel_url=request.url_for("pricing"),
    )
    return {"url": checkout_url}

@app.post("/tasks/send-notification")
async def queue_notification(request: Request, data: dict):
    task_id = await send_notification_email.kiq(
        user_id=request.user.id,
        message=data["message"]
    )
    return {"task_id": task_id}

# Run: uvicorn app:app --reload
```

---

## Environment Variables Template

```bash
# .env

# General
DEBUG=true
SECRET_KEY=your-secret-key-here

# Database
DATABASE_URL=postgresql://user:password@localhost/eden_db

# Redis (optional - for tasks, websockets, cache)
REDIS_URL=redis://localhost:6379

# Stripe
STRIPE_API_KEY=sk_test_... (or sk_live_... for production)
STRIPE_WEBHOOK_SECRET=whsec_...

# Email (for background tasks)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

---

## Quick Activation Checklist

- [ ] **HTMX** - Add `from eden.htmx import HtmxResponse` in routes
- [ ] **WebSockets** - Create `WebSocketRouter` and register routes
- [ ] **Background Tasks** - Call `app.setup_tasks()` and use `@app.task()`
- [ ] **Stripe** - Call `app.configure_payments(StripeProvider(...))` with env vars
- [ ] **Tenancy** - Call `app.add_middleware("tenant", ...)` and use `TenantMixin`

All features are production-ready. Just copy-paste the activation code above! 🚀
