# 🌿 Eden Framework

**The Premium, Developer-First Python Web Framework.**

Eden is a high-performance, async-first web framework designed for developers who value aesthetics, security, and developer experience. Built on top of Starlette and SQLAlchemy 2.0, Eden provides a curated suite of tools that work together seamlessly, allowing you to focus on building "wow" applications from the first line of code.

---

## ✨ Key Features

- **💎 Premium Design System:** Built-in support for modern aesthetics, including Glassmorphism and specialized typography (Plus Jakarta Sans).
- **📝 Gorgeous Templating:** A custom directive-based template engine built on Jinja2 that keeps your HTML clean and readable.
- **🛠️ Zero-Config ORM:** SQLAlchemy 2.0 wrapped in a Django-inspired interface with automatic session injection.
- **🛡️ Built-in Security:** First-class middleware for CSRF, security headers, rate limiting, and API Token authentication.
- **🏢 Native Multi-Tenancy:** Async-safe row-level isolation built into the core ORM.
- **💳 Payment Integration:** Ready-to-use Stripe integration for subscriptions and checkouts.
- **☁️ Cloud Storage:** Pluggable storage backends with native S3 support.
- **🚥 Premium Debug UI:** A stunning, glassmorphic error interface for effortless debugging.

---

## 🛠️ Installation

```bash
pip install eden-framework
```

---

## 🚀 Quickstart

Create `app.py`:

```python
from eden import Eden
from eden.db import Database

db = Database("sqlite+aiosqlite:///db.sqlite3")
app = Eden(debug=True)
app.db = db

async def home(request):
    return {"message": "Welcome to Eden! 🌿"}

@app.on_startup
async def startup():
    await db.connect(create_tables=True)

app.get('/')(home)

if __name__ == "__main__":
    app.run(port=8888)
```

Run your app:
```bash
python app.py
```

---

## 📝 Modern Templating Syntax

Eden replaces the verbose Jinja2 tags with a clean, brace-based `@directive` syntax. It's fully line-preserving, ensuring that error traces point to the exact location in your original source.

### Control Flows
```html
@if (user.is_authenticated) {
    <div class="welcome">Welcome back, {{ user.name }}!</div>
} @else {
    <a href="/login">Please sign in</a>
}

@for (post in posts) {
    <article>{{ post.title }}</article>
} @empty {
    <p>No posts found.</p>
}
```

### Components & Slots
Create reusable UI components with ease.
```html
@component("card", title="Profile", shadow="lg") {
    @slot("header") {
        <img src="{{ user.avatar }}" alt="Avatar">
    }
    <p>{{ user.bio }}</p>
}
```

### Variable Assignment & Includes
```html
@let accent_color = "#2563EB"
@extends("layouts/base")
@include("partials/nav")
@csrf
```

---

## 🗄️ Fluent ORM

Eden's ORM eliminates the boilerplate of session management. Just define your model and start querying.

```python
from eden.db import EdenModel, StringField, BoolField

class User(EdenModel):
    name: Mapped[str] = StringField(max_length=100)
    email: Mapped[str] = StringField(max_length=255, unique=True)
    is_active: Mapped[bool] = BoolField(default=True)

# 🚀 Session-less queries (Auto-injected)
users = await User.filter(is_active=True)
user = await User.get(id=user_id)

# 📝 Creation & Updates
new_user = await User.create(name="Eden", email="hello@eden.dev")
await new_user.update(name="Eden Framework")
```

---

## 🚥 Premium Debug Experience

Say goodbye to cryptic error messages. Eden's debug page is a full-featured diagnostic tool designed to look as good as your application.

- **High-Fidelity Code Explorer:** A gorgeous, syntax-highlighted code viewer that uses advanced traceback recovery to find the exact line in your original source, even for complex template errors.
- **Fuzzy Suggestions:** Intelligent diagnostics that suggest fixes for undefined variables (e.g., "Did you mean `user`?").
- **Variable Snapshots:** Inspect the live state of your template variables and request context at the moment of failure.
- **Environment Health:** Instant visibility into system, Python, and framework metadata.

![Eden Debug UI](file:///c:/ideas/eden/eden_error_page_demo_1772608981343.webp)

---

## 🛡️ Robust Security & Middleware

Eden makes it effortless to protect your application with a unified middleware registry.

```python
from eden import Eden

app = Eden(debug=True)

# 🛡️ Built-in security & optimization
app.add_middleware("security")      # CSP, HSTS, XSS Protection
app.add_middleware("csrf")          # Cross-Site Request Forgery
app.add_middleware("ratelimit", max_requests=60)
app.add_middleware("cors", allow_origins=["*"])
app.add_middleware("gzip")          # Compression

# 🛡️ Role-Based Access Control (RBAC)
from eden.auth import roles_required, permissions_required

@app.get("/admin-only")
@roles_required(["admin"])
async def admin_area():
    return {"message": "Welcome, Admin"}
```

---

## ⚡ Integrated SaaS Features

Eden comes packed with everything you need to build a production-ready SaaS.

### 🔑 API Token Authentication
Securely authenticate requests using hashed API keys.
```python
from eden import APIKey

# Generate a new key for a user
key_obj, raw_key = await APIKey.generate(user_id=user.id, name="Pro Plan Key")
```

### 🏢 Multi-Tenancy
Scope your data automatically to the current tenant.
```python
class Post(EdenModel, TenantMixin):
    title: Mapped[str] = StringField()

# middleware handles scoping; queries are auto-filtered
posts = await Post.all() 
```

### 📧 Mail Service
Send beautiful, template-based emails with SMTP or Console backends.
```python
from eden import send_mail

await send_mail(
    subject="Welcome to Eden",
    recipient="hello@example.com",
    template="emails/welcome.html",
    context={"name": "Developer"}
)
```

### 💳 Payments & Billing
Native Stripe integration for managing customers and subscriptions.
```python
from eden import CustomerMixin

class User(EdenModel, BaseUser, CustomerMixin):
    ...

# Create checkout sessions or handle webhooks with WebhookRouter
```

### ☁️ S3 Storage
Store media files in the cloud with ease.
```python
from eden import storage, S3StorageBackend

storage.register("s3", S3StorageBackend(bucket="my-bucket"))
url = await storage.save("avatar.png", content)
```

### 🛠️ Professional Admin Panel
Manage your models with a premium, auto-generated dashboard.
```python
from eden.admin import admin

admin.register(User)
app.mount_admin() # Dashboard at /admin/
```

## 🏗️ Project Structure

A standard Eden project follows a clean, scalable layout:

```text
my_project/
├── app.py              # Application entry point
├── static/             # Assets (CSS, JS, Images)
├── templates/          # Eden HTML templates
├── models/             # Database models
├── routes/             # Route handlers
└── .env                # Configuration
```

---

## 📜 Roadmap

- [x] **API Token Auth:** Prefix-based secure key management.
- [x] **Multi-Tenancy:** Row-level isolation middleware and mixins.
- [x] **Email Service:** SMTP and template rendering support.
- [x] **Admin Panel:** Premium auto-generated CRUD interface.
- [x] **Payment Integration:** Stripe-first billing primitives.
- [x] **S3 Storage:** Async cloud storage backend.
- [ ] **Eden CLI:** Scaffolding and automated migrations.
- [ ] **Native HTMX Integration:** Deeply integrated partial rendering and fragment control.
- [ ] **Real-time:** Native WebSocket support for reactive UIs.

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details on how to get started.

---

**Built with ❤️ for developers who love beautiful code.**
