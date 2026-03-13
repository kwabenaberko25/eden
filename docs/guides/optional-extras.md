# Optional Extras 📦

## WebhookRouter Pattern

Handle payment webhooks with automatic routing:

```python
from eden.payments.webhooks import WebhookRouter

webhooks = WebhookRouter()

@webhooks.on("checkout.session.completed")
async def handle_checkout(event_data: dict):
    # User purchased something
    session_id = event_data["id"]
    customer_id = event_data["customer"]
    
    # Create subscription or charge record
    customer = await Customer.get(stripe_id=customer_id)
    await Order.create(customer=customer, session_id=session_id)

@webhooks.on("customer.subscription.updated")
async def handle_subscription_update(event_data: dict):
    # Subscription changed (upgraded, downgraded, cancelled)
    subscription_id = event_data["id"]
    status = event_data["status"]
    
    sub = await Subscription.get(stripe_id=subscription_id)
    sub.status = status
    await sub.save()

# Mount in your app
@app.post("/webhooks/stripe")
async def stripe_webhook(request):
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    # Verify and parse
    event = stripe.verify_webhook_signature(payload, sig_header)
    
    # Route to handler
    await webhooks.dispatch(event["type"], event["data"])
    
    return json({"ok": True})
```

Eden's core is lightweight and focused. Extended features are available as **optional extras** that you install only when needed.

## Quick Reference

| Extra | Purpose | Key Class | Install |
|-------|---------|-----------|----------|
| `[payments]` | Stripe billing, subscriptions | `StripeProvider` | `pip install eden-framework[payments]` |
| `[storage]` | S3, Supabase, local file storage | `S3StorageBackend` | `pip install eden-framework[storage]` |
| `[databases]` | MySQL, SQLite, Oracle support | `Database` | `pip install eden-framework[databases]` |
| `[tasks]` | Background jobs, cron tasks | `@Task()` | `pip install eden-framework[tasks]` |
| `[mail]` | Email, SMTP, templates | `EmailMessage` | `pip install eden-framework[mail]` |
| `[ai]` | Vector embeddings, semantic search | `VectorModel` | `pip install eden-framework[ai]` |

---

## Installation Patterns

### Minimal Installation (Core Only)
```bash
pip install eden-framework
```
**Size**: ~3 MB | **Dependencies**: 12 core packages

**What you get:**
- Web application framework
- Async ORM with SQLAlchemy 2.0
- Authentication (API keys, sessions)
- Multi-tenancy
- Admin panel
- WebSocket support
- CLI tools

---

### With Optional Extras

Install specific features bundled together:

```bash
# Payment processing with Stripe
pip install eden-framework[payments]

# Cloud storage (S3, Supabase, etc.)
pip install eden-framework[storage]

# Databases beyond PostgreSQL
pip install eden-framework[databases]

# Background tasks with Taskiq
pip install eden-framework[tasks]

# Email/SMTP integration
pip install eden-framework[mail]

# AI/ML (vector embeddings with pgvector)
pip install eden-framework[ai]

# Everything
pip install eden-framework[all]
```

### Mix and Match
```bash
# Multiple extras
pip install eden-framework[payments,storage,tasks]
```

---

## Feature Breakdown

### `[payments]` - Stripe Integration 💳

Full payment processing and subscription management.

**Includes:**
- `StripeProvider` for payments
- `Customer` model with billing portal
- `Subscription` model for recurring charges
- `WebhookRouter` for event handling
- Payment events (charge.succeeded, customer.subscription.updated)
- Webhook signature verification

**Setup:**

```bash
pip install eden-framework[payments]
```

```python
import os
from eden.payments import StripeProvider

# In eden.json or environment
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# Initialize
stripe = StripeProvider(
    secret_key=STRIPE_SECRET_KEY,
    publishable_key=STRIPE_PUBLISHABLE_KEY
)
```

**Common Tasks:**

```python
from eden.payments import Customer, Subscription

# Create customer
customer = await Customer.create(
    user=request.user,
    stripe_customer_id=stripe_id
)

# Create subscription
sub = await Subscription.create(
    customer=customer,
    plan="pro",
    stripe_subscription_id=sub_id
)

# Listen for webhooks
@app.post("/webhooks/stripe")
async def stripe_webhook(request):
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    event = stripe.verify_webhook_signature(payload, sig_header)
    
    if event['type'] == 'charge.succeeded':
        # Handle charge
        pass
```

**Docs**: See [Payment Processing with Stripe](../tutorial/task8_saas.md#payments)

---

### `[storage]` - Cloud Storage Backends 🌩️

Flexible file storage across multiple cloud providers and local filesystem.

**Includes:**
- `LocalStorageBackend` - File system storage
- `S3StorageBackend` - Amazon S3
- `SupabaseStorageBackend` - Supabase Storage
- Plugin system for custom backends

**Setup:**

```bash
pip install eden-framework[storage]
```

```python
from eden.storage import S3StorageBackend, LocalStorageBackend

# Local storage
storage = LocalStorageBackend(path="/var/uploads")

# S3
storage = S3StorageBackend(
    bucket="my-bucket",
    region="us-east-1",
    # Uses AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY from env
)

# Supabase
storage = SupabaseStorageBackend(
    url="https://xxxx.supabase.co",
    key="anon-key",
    bucket="my-bucket"
)
```

**S3 Presigned URLs (Private Files):**

```python
# Generate time-limited access URL for private S3 files
presigned_url = await storage.get_presigned_url(
    key="private/documents/contract.pdf",
    expires_in=3600  # URL valid for 1 hour
)

# Send to client for download
return json({
    "download_url": presigned_url,
    "expires_in": 3600
})

# Client can download without AWS credentials
```

**Common Tasks:**

```python
# Save file
key = await storage.save(
    content=request.files['upload'],
    name="profile.jpg",
    folder="users"
)
# Returns: "users/profile_a1b2c3de.jpg"

# Get public URL
url = storage.url(key)  # https://bucket.s3.amazonaws.com/users/profile_a1b2c3de.jpg

# Delete
await storage.delete(key)

# For S3: Get presigned URL (for private files)
if hasattr(storage, 'get_presigned_url'):
    presigned = await storage.get_presigned_url(key, expires_in=3600)
```

---

### `[databases]` - Additional Database Support 🗄️

Support for databases beyond PostgreSQL.

**Includes:**
- MySQL/MariaDB drivers
- SQLite async support
- Oracle database support

**Setup:**

```bash
pip install eden-framework[databases]
```

```python
from eden import Database

# MySQL
db = Database(
    url="mysql+asyncmy://user:pass@localhost/dbname"
)

# SQLite (great for testing)
db = Database(
    url="sqlite+aiosqlite:///./test.db"
)
```

---

### `[tasks]` - Background Job Processing ⏰

Asynchronous task queue for long-running operations.

**Includes:**
- Taskiq integration
- Task scheduling (periodic jobs)
- Redis backend (optional)
- Multi-broker support

**Setup:**

```bash
pip install eden-framework[tasks]
```

```python
from eden.tasks import Task, broker

# Define a task
@Task()
async def send_welcome_email(user_id: int):
    user = await User.get(id=user_id)
    await send_email(user.email, "Welcome!")

# Queue the task
await send_welcome_email.delay(user_id=123)

# Or schedule it
await send_welcome_email.schedule(
    user_id=123,
    delay=3600  # 1 hour from now
)
```

**Running the worker:**

```bash
eden tasks worker
eden tasks scheduler  # For periodic tasks
```

---

### `[mail]` - Email & SMTP 📧

Send transactional and templated emails.

**Includes:**
- SMTP backend
- SendGrid integration (optional)
- Email templates
- Attachments support

**Setup:**

```bash
pip install eden-framework[mail]
```

```python
from eden.mail import EmailMessage, send_mail

# Using SMTP
message = EmailMessage(
    subject="Welcome!",
    body="Thanks for signing up.",
    from_email="noreply@example.com",
    to=["user@example.com"]
)
await message.send()

# Or via shortcut
await send_mail(
    subject="Confirm Email",
    message="Click here to confirm",
    recipient_list=["user@example.com"]
)
```

**Templates:**

```python
await send_mail(
    template="welcome",  # renders templates/emails/welcome.html
    context={"user": request.user},
    recipient_list=[request.user.email]
)
```

---

### `[ai]` - AI & Vector Embeddings 🤖

Build semantic search and RAG systems with pgvector.

**Includes:**
- `VectorModel` base class
- `VectorField` for embeddings
- `semantic_search()` method
- pgvector + PostgreSQL integration

**Setup:**

```bash
pip install eden-framework[ai]
pip install pgvector  # PostgreSQL extension
```

```python
from eden.db.ai import VectorModel, VectorField
from eden import f, Mapped

class Document(VectorModel):
    title: Mapped[str] = f()
    content: Mapped[str] = f()
    embedding: Mapped[list[float]] = VectorField(dimensions=1536)

# Semantic search
results = await Document.semantic_search(
    embedding=query_vector,
    limit=10
)
```

**Using with OpenAI:**

```python
import openai

# Get embedding from OpenAI
response = openai.Embedding.create(
    input="find similar documents",
    model="text-embedding-3-small"
)
embedding = response['data'][0]['embedding']

# Search
docs = await Document.semantic_search(embedding)
```

---

### `[all]` - Everything

Install all optional extras at once:

```bash
pip install eden-framework[all]
```

Equivalent to:
```bash
pip install eden-framework[payments,storage,databases,tasks,mail,ai]
```

---

## Managing Dependencies

### Production Builds

Use minimal setup for smaller containers:

```dockerfile
# Minimal production image
FROM python:3.11-slim
RUN pip install eden-framework
```

### Full-Featured Setup

For development or multi-feature applications:

```dockerfile
# Full-featured image
FROM python:3.11
RUN pip install eden-framework[all]
```

### Conditional Imports

Check for optional features at runtime:

```python
try:
    from eden.payments import StripeProvider
    HAS_PAYMENTS = True
except ImportError:
    HAS_PAYMENTS = False

if HAS_PAYMENTS:
    # Payment routes
    @app.get("/checkout")
    async def checkout(request):
        pass
```

---

## Troubleshooting

### Module Not Found Errors

**Problem**: `ModuleNotFoundError: No module named 'eden.payments'`

**Solution**: Install the required extra:
```bash
pip install eden-framework[payments]
```

### Missing Dependencies

**Problem**: `No module named 'stripe'` or similar

**Solution**: Check which extras provide that feature in the table above, then install:
```bash
pip install eden-framework[that-extra]
```

### Size Concerns

- **Core only**: ~3 MB
- **[payments]**: +5 MB (Stripe client)
- **[storage]**: +2 MB (Cloud SDKs)
- **[tasks]**: +8 MB (Taskiq + Redis)
- **[ai]**: +3 MB (pgvector)

For Docker, use multi-stage builds to separate build and runtime:

```dockerfile
FROM python:3.11 as builder
RUN pip install --target /app eden-framework[all]

FROM python:3.11-slim
COPY --from=builder /app /app
```

---

**Next Steps**: Choose the extras you need and follow the quick setup above. Visit individual feature docs for advanced usage.
