# Task 8: Integrate SaaS Features

**Goal**: Leverage Eden's "batteries-included" ecosystem to add professional SaaS features like an Admin portal, emails, cloud storage, and automated payments.

---

## 🖥️ Step 8.1: Built-in Admin Portal

Eden can auto-generate a stunning, secure admin interface from your database models with zero code.

**File**: `app/__init__.py`

```python
from eden import Eden
from eden.db import Model, f
from eden.admin import admin

class User(Model):
    email: str = f(unique=True)

def create_app() -> Eden:
    app = Eden(secret_key="dev-secret")
    
    # 1. Register your models with the Admin site
    admin.register(User)
    
    # 2. Mount the Admin router at a specific path
    app.mount_admin(path="/portal")
    
    return app
```

### 🛰️ Verification

Visit `http://127.0.0.1:8000/portal` to manage your users directly through the UI.

---

## 📧 Step 8.2: Enterprise Mail Delivery

Eden provides a unified interface for sending emails, with backends for development (Console), SMTP, and Mailgun.

**File**: `app/__init__.py`

```python
from eden import Eden
from eden.mail import SMTPBackend

app = Eden(secret_key="dev-secret")

# Configure the production SMTP backend
smtp = SMTPBackend(
    host="smtp.sendgrid.net",
    port=587,
    username="apikey",
    password="SG.your_api_key_here"
)
app.configure_mail(smtp)
```

**Usage**:

```python
from eden.mail import send_mail
from eden import Eden

app = Eden()

async def welcome_new_user(email: str, name: str):
    await send_mail(
        subject="Welcome to Eden! 🌿",
        recipient=email,
        template="emails/welcome.html",
        context={"name": name}
    )
```

---

## ☁️ Step 8.3: Unified Storage (S3 / Local)

Swap between local files and cloud storage without changing your code.

```python
from eden.storage import storage
from eden.storage.s3 import S3StorageBackend
from eden.db import Model, StringField

class User(Model):
    avatar_url: str = StringField()

# Register an S3 bucket
# storage.register("cloud", S3StorageBackend(
#     bucket="my-saas-media",
#     access_key="...",
#     secret_key="..."
# ), default=True)

# Usage in a view
async def upload_avatar(request):
    files = await request.form()
    file = files['avatar']
    
    # Automatically uploads to default storage (S3 in prod, local in dev)
    path = await storage.save('avatars/', file)
    
    # Update user
    user = request.user
    user.avatar_url = await storage.url(path)
    await user.save()
    
    return {"message": "Avatar updated", "url": user.avatar_url}
```

---

## Payments

## 💳 Step 8.4: Stripe Payment Integration

Process payments securely using the Stripe integration:

```python
from eden.payments import stripe_client
from eden.db import Model, StringField, FloatField

class Subscription(Model):
    user_id: int = StringField()
    stripe_subscription_id: str = StringField()
    plan: str = StringField()
    amount: float = FloatField()

async def create_subscription(request):
    """Create a Stripe subscription for the user."""
    try:
        # stripe_client is a proxy to the stripe SDK
        subscription = await stripe_client.Subscription.create(
            customer=request.user.stripe_customer_id,
            items=[{"price": "price_1Abc..."}]  # Your Stripe price ID
        )
        
        # Store subscription ID
        await Subscription.create(
            user_id=request.user.id,
            stripe_subscription_id=subscription.id,
            plan="pro",
            amount=99.00
        )
        
        return {
            "message": "Subscription created",
            "subscription_id": subscription.id
        }
    except Exception as e:
        return {"error": f"Payment failed: {str(e)}"}, 400
```

Handle Stripe webhooks automatically:

```python
from eden.routing import Router
from eden.payments import stripe_webhook
from eden.db import Model, StringField

class Subscription(Model):
    stripe_subscription_id: str = StringField()
    status: str = StringField()

payment_router = Router()

@payment_router.post("/webhook")
@stripe_webhook
async def handle_stripe_event(request):
    """Automatically triggered on Stripe events."""
    event = await request.json()
    if event['type'] == "invoice.payment_succeeded":
        subscription_id = event['data']['object']['subscription']
        sub = await Subscription.filter(stripe_subscription_id=subscription_id).first()
        if sub:
            sub.status = "active"
            await sub.save()
    
    return {"success": True}
```

---

## 🎯 Step 8.5: Native Multi-Tenancy

Eden features "Zero-Leak" multi-tenancy. By setting `__tenant_aware__ = True`, Eden automatically injects `tenant_id` filters into every query, ensuring users *only* see data belonging to their organization.

```python
from eden.db import Model, IntField, StringField, Mapped
from eden.routing import Router

class Document(Model):
    # Enable automatic multi-tenant isolation
    __tenant_aware__ = True
    
    tenant_id: Mapped[int] = IntField(index=True)
    title: Mapped[str] = StringField()
    content: Mapped[str] = StringField()

doc_router = Router()

# In your routes - isolation is now IMPLICIT
@doc_router.get("/")
async def list_documents(request):
    # No filter needed! Eden uses request.tenant_id automatically
    docs = await Document.all()
    return {"documents": [d.to_dict() for d in docs]}
```

---

## 📊 Step 8.6: Analytics & Metrics

Track application health and user behavior:

```python
from eden import Eden
from eden.telemetry import record_metric
from eden.db import Model, IntField, StringField, DateTimeField, FloatField, Mapped, Sum, Count
from eden.routing import Router
from datetime import datetime

class UserAction(Model):
    """Track what users do in your app."""
    user_id: Mapped[int] = IntField()
    action: Mapped[str] = StringField() 
    created_at: Mapped[datetime] = DateTimeField()

class Order(Model):
    total_price: Mapped[float] = FloatField()

app = Eden(secret_key="dev-secret")

# In your routes
@app.middleware("http")
async def track_actions(request, call_next):
    """Record all user actions for analytics."""
    response = await call_next(request)
    
    if hasattr(request, "user") and request.user:
        await UserAction.create(
            user_id=request.user.id,
            action=request.method
        )
        # Record a metric for monitoring
        record_metric("user_action", 1, tags={"action": request.method})
    
    return response

# Simple analytics endpoint
analytics_router = Router()

@analytics_router.get("/summary")
async def analytics_summary(request):
    """Get dashboard analytics."""
    return await Order.aggregate(
        total_revenue=Sum("total_price"),
        order_count=Count("id")
    )
```

---

### **Next Task**: [Deploying the Application](./task9_deployment.md)
