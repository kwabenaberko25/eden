# Integrated SaaS Services ☁️

Eden comes pre-loaded with the essential services required to build, bill, and scale a modern SaaS.

## Mailer Service 📧

Send beautiful, template-based emails with zero boilerplate.

### Configuration

Eden uses the `EDEN_SMTP_URL` environment variable for production mail.

```text
EDEN_SMTP_URL=smtp://user:pass@smtp.gmail.com:587
```


### Basic Usage

```python
from eden import send_mail

await send_mail(
    to="customer@example.com",
    subject="Subscription Active",
    template="emails/invoice.html",
    context={"amount": "$19.00"}
)
```

---

## Billing & Subscriptions (Stripe) 💳

Eden provides a high-level wrapper around Stripe for effortless subscription management.

### Stripe Checkout

```python
# Create a checkout session
session_url = await user.billing.create_checkout_session(plan_id="pro_monthly")
```

### Stripe Webhooks 🪝

Eden handles webhook signature verification automatically.

```python
@app.post("/webhooks/stripe")
async def stripe_webhook(request):
    event = await app.billing.handle_webhook(request)
    if event.type == "checkout.session.completed":
        # Handle logic
        pass
    return {"status": "success"}
```

---

## Cloud Storage 📂

Manage file uploads across different backends. Configuration is handled in the environment.

| Backend | Class | Requirements |
| :--- | :--- | :--- |
| `local` | `eden.storage.LocalStorageBackend` | None (built-in). |
| `s3` | `eden.storage_backends.S3StorageBackend` | `aioboto3`, AWS keys/bucket config. |
| `supabase` | `eden.storage_backends.SupabaseStorageBackend` | `supabase`, project URL/key. |

```python
from eden.storage import LocalStorageBackend, storage

# Register the local backend (default)
local = LocalStorageBackend(base_path="./media", base_url="/media/")
storage.register("local", local, default=True)

# Save a file
path = await storage.get("local").save(upload_file)
url = storage.get("local").url(path)
```

---

## Third-Party Integration Pattern: OpenAI 🤖

Eden encourages encapsulating logic in Service classes for clean architecture.

```python
# app/services/ai.py
from eden import Service
import openai

class AIService(Service):
    async def summarize_task(self, task_content: str):
        response = await openai.chat.completions.create(
            messages=[{"role": "user", "content": f"Summarize: {task_content}"}],
            model="gpt-4"
        )
        return response.choices[0].message.content

# Usage in a Route
@app.post("/tasks/{id}/summarize")
async def summarize(request, id: int):
    task = await Task.get(id=id)
    summary = await AIService.summarize_task(task.content)
    await task.update(summary=summary)
    return {"status": "updated"}
```

---

## Core Storage API

```python
from eden import storage

# Save to the default storage
file_url = await storage.save("invoices/001.pdf", content)

# Retrieve a signed URL
signed_url = await storage.get_url("secret_document.zip", expires=3600)
```

---

## Caching 🚥

Speed up your application by caching expensive views or data.

### View Decorator

```python
from eden.cache import cache_view

@app.get("/stats")
@cache_view(ttl=300) # Cache for 5 minutes
async def stats(request):
    return {"data": await get_slow_stats()}
```

### Manual Caching

```python
await app.cache.set("key", "value", ttl=60)
val = await app.cache.get("key")
```


**Next Steps**: [The Admin Panel](admin.md)
