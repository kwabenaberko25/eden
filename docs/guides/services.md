# Integrated SaaS Services ☁️

Eden comes pre-loaded with the essential services required to build, bill, and scale a modern SaaS.

## Mailer Service 📧

Send beautiful, template-based emails with zero boilerplate.

### Configuration

```text
MAIL_BACKEND=smtp
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USER=...
MAIL_PASSWORD=...
```

### Basic Usage

```python
from eden import send_mail

await send_mail(
    subject="Subscription Active",
    recipient="customer@example.com",
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

| Backend | Description | Requirements |
| :--- | :--- | :--- |
| `local` | Default. Saves to the app's `storage/` dir. | None. |
| `s3` | AWS S3 or compatible (MinIO, DigitalOcean). | `boto3`, keys/bucket config. |
| `supabase` | Supabase Storage. | `supabase` client keys. |

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
from eden.cache import cache

@app.get("/stats")
@cache(expire=300) # Cache for 5 minutes
async def stats(request):
    return {"data": await get_slow_stats()}
```

### Manual Caching

```python
await app.cache.set("key", "value", expire=60)
val = await app.cache.get("key")
```

**Next Steps**: [The Admin Panel](admin.md)
