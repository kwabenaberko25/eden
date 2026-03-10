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
    avatar_url = await storage.save(
        "avatars/user_1.jpg", 
        files["avatar"].file
    )
    return {"url": avatar_url}
```

---

## 💰 Step 8.4: Stripe Integration

Turn on subscriptions and one-time payments with the native Stripe provider.

```python
from eden.payments import StripeProvider

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
