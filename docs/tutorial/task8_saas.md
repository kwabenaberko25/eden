# Task 8: Integrate SaaS Features

**Goal**: Leverage Eden's "batteries-included" ecosystem to add professional SaaS features like an Admin portal, emails, cloud storage, and automated payments.

---

## 🖥️ Step 8.1: Built-in Admin Portal

Eden can auto-generate a stunning, secure admin interface from your database models with zero code.

**File**: `app/__init__.py`

```python
from eden.admin import admin
from app.models import User

def create_app() -> Eden:
    app = Eden(...)
    
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
from eden.mail import SMTPBackend

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
from eden import send_mail

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
from eden import storage, S3StorageBackend

# Register an S3 bucket
storage.register("cloud", S3StorageBackend(
    bucket="my-saas-media",
    aws_access_key_id="...",
    aws_secret_access_key="..."
), default=True)

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

async def create_subscription(request):
    """Create a Stripe subscription for the user."""
    try:
        subscription = await stripe_client.subscriptions.create(
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
    except stripe_client.StripeException as e:
        return {"error": f"Payment failed: {str(e)}"}, 400
```

Handle Stripe webhooks automatically:
```python
from eden.payments import stripe_webhook

@payment_router.post("/webhook")
@stripe_webhook
async def handle_stripe_event(event):
    """Automatically triggered on Stripe events."""
    if event.type == "invoice.payment_succeeded":
        subscription_id = event.data.object.subscription
        sub = await Subscription.filter(stripe_subscription_id=subscription_id).first()
        sub.status = "active"
        await sub.save()
    
    return {"success": True}
```

---

## 🎯 Step 8.5: Multi-Tenancy (Lightweight)

Support multiple customers with isolated data:

```python
from eden.tenancy import Tenant

class Tenant(Model):
    """Represent a SaaS customer."""
    name: Mapped[str] = f(max_length=255)
    slug: Mapped[str] = f(unique=True, index=True)  # subdomain identifier
    owner_id: Mapped[int] = f(foreign_key="user.id")
    plan: Mapped[str] = f(default="free")  # free, pro, enterprise
    created_at: Mapped[datetime] = f(default=datetime.utcnow)

class Document(Model):
    """Documents belong to a tenant, not globally."""
    tenant_id: Mapped[int] = f(foreign_key="tenant.id", index=True)
    title: Mapped[str] = f()
    
    # Ensure queries are always scoped to the current tenant
    @classmethod
    async def for_tenant(cls, tenant_id: int):
        return cls.filter(tenant_id=tenant_id)

# In your routes - always scope to current tenant
@doc_router.get("/")
async def list_documents(request):
    # Get the current tenant from the request context
    tenant = request.tenant
    
    # Only return documents for this tenant
    docs = await Document.for_tenant(tenant.id).all()
    return {"documents": [d.to_dict() for d in docs]}
```

---

## 📊 Step 8.6: Analytics & Metrics

Track application health and user behavior:

```python
from eden.telemetry import record_metric

class UserAction(Model):
    """Track what users do in your app."""
    user_id: Mapped[int] = f(foreign_key="user.id")
    action: Mapped[str]  # "login", "upload", "download"
    metadata: Mapped[dict] = f(json=True)
    created_at: Mapped[datetime] = f(default=datetime.utcnow)

# In your routes
@app.middleware("http")
async def track_actions(request, call_next):
    """Record all user actions for analytics."""
    response = await call_next(request)
    
    if request.user:
        await UserAction.create(
            user_id=request.user.id,
            action=request.method,
            metadata={
                "path": request.url.path,
                "status": response.status_code
            }
        )
        
        # Record a metric for monitoring
        record_metric("user_action", 1, tags={"action": request.method})
    
    return response

# Simple analytics endpoint
@analytics_router.get("/summary")
@roles_required("admin")
async def analytics_summary(request):
    """Get dashboard analytics."""
    total_users = await User.count()
    active_today = await UserAction.filter(
        created_at__gte=datetime.utcnow().replace(hour=0, minute=0, second=0)
    ).distinct().count('user_id')
    
    return {
        "total_users": total_users,
        "active_today": active_today,
        "revenue": 44000
    }
```

---

# Initialize the payments engine
stripe = StripeProvider(api_key="sk_test_...")
app.configure_payments(stripe)

# Create a Checkout Session
checkout_url = await stripe.create_checkout_session(
    customer_email="user@dev.com",
    price_id="price_H5ggHdqxyz",
    success_url="https://myapp.com/success"
)
```

---

### **Next Task**: [Deploying the Application](./task9_deployment.md)
