# SaaS Payments & Subscriptions

> **Monetize your SaaS with Eden's Provider-Agnostic Payments Layer**

Eden provides a robust abstraction layer for handling subscriptions, one-time payments, and billing portals. While it defaults to **Stripe**, the architecture is designed to support multiple providers without changing your business logic.

---

## 1. Quick Start: Stripe Integration

To get started, install the `stripe` python package and configure the provider in your main entry point.

```bash
uv add stripe
```

### Configuration

```python
# app.py
from eden import Eden
from eden.payments import StripeProvider

app = Eden()

# Initialize the provider
stripe_provider = StripeProvider(
    api_key=settings.STRIPE_SECRET_KEY,
    webhook_secret=settings.STRIPE_WEBHOOK_SECRET
)

# Register it with the app
app.configure_payments(stripe_provider)
```

---

## 2. The `BillableMixin`

The easiest way to integrate payments into your models is using the `BillableMixin`. This adds fields for `stripe_customer_id`, `subscription_id`, and `billing_status` automatically.

```python
from eden.db import Model
from eden.payments import BillableMixin

class Tenant(Model, BillableMixin):
    __tablename__ = "tenants"
    name = Column(String)
    # Plus inherited: stripe_customer_id, subscription_status, etc.
```

---

## 3. Creating a Checkout Session

Redirect users to a secure checkout page hosted by your provider.

```python
from eden import Response, redirect
from eden.payments import get_payment_provider

@app.post("/subscribe")
async def create_subscription(request):
    provider = get_payment_provider()
    user = request.user
    
    # 1. Ensure user has a provider customer ID
    if not user.stripe_customer_id:
        customer_id = await provider.create_customer(user.email, name=user.name)
        user.stripe_customer_id = customer_id
        await user.save()
        
    # 2. Create the checkout session
    checkout_url = await provider.create_checkout_session(
        customer_id=user.stripe_customer_id,
        price_id="price_H5ggv909sdj", # From your Stripe Dashboard
        success_url=f"{request.base_url}/billing/success",
        cancel_url=f"{request.base_url}/billing/cancel"
    )
    
    return redirect(checkout_url)
```

---

## 4. Handling Webhooks

Webhooks are critical for keeping your database in sync with payment events (e.g., successful renewals or cancellations).

```python
# app/routes/webhooks.py
from eden.payments import handle_webhook

@app.post("/webhook/stripe")
async def stripe_webhook(request):
    # This helper verifies the signature and triggers 
    # internal app events based on the event type.
    await handle_webhook(
        request, 
        on_success="subscription.activated", 
        on_failure="subscription.payment_failed"
    )
    return Response(status_code=200)
```

### Listening for Payment Events

```python
@app.on("subscription.activated")
async def on_sub_active(event):
    data = event.data
    customer_id = data["customer"]
    
    tenant = await Tenant.get_by(stripe_customer_id=customer_id)
    tenant.subscription_status = "active"
    tenant.plan = "pro"
    await tenant.save()
```

---

## 5. The Billing Portal

Let users manage their own subscriptions, update credit cards, and download invoices without writing a single line of UI code.

```python
@app.get("/billing/manage")
@auth_required
async def manage_billing(request):
    provider = get_payment_provider()
    
    portal_url = await provider.create_portal_session(
        customer_id=request.user.stripe_customer_id,
        return_url=f"{request.base_url}/dashboard"
    )
    
    return redirect(portal_url)
```

---

## 6. Premium UI: Pricing Table

Use Eden's design system to build a beautiful pricing table that converts.

```html
@extends("layouts/base")

@section("content")
<div class="grid grid-cols-1 md:grid-cols-3 gap-8 py-12">
    <!-- Pro Plan -->
    <div class="glass p-8 rounded-2xl border-emerald-500/30 flex flex-col relative overflow-hidden">
        <div class="absolute top-0 right-0 bg-emerald-500 text-black text-[10px] font-bold px-3 py-1 uppercase tracking-widest">
            Recommended
        </div>
        
        <h3 class="text-xl font-bold mb-2">Pro Plan</h3>
        <p class="text-slate-400 text-sm mb-6">Perfect for small teams scaling fast.</p>
        
        <div class="text-4xl font-black mb-8">
            $49<span class="text-lg font-normal text-slate-500">/mo</span>
        </div>
        
        <ul class="space-y-4 mb-10 flex-1">
            <li class="flex items-center gap-2">
                <i class="fa fa-check text-emerald-500"></i> Unlimited Projects
            </li>
            <li class="flex items-center gap-2 text-slate-500">
                <i class="fa fa-check"></i> Advanced Analytics
            </li>
        </ul>
        
        <button hx-post="/subscribe/pro" class="bg-emerald-600 hover:bg-emerald-500 py-3 rounded-lg font-bold transition">
            Get Started
        </button>
    </div>
</div>
@endsection
```

---

## Best Practices

- ✅ **Verification**: Always use `verify_webhook_signature` to prevent spoofing.
- ✅ **Graceful Failures**: Map provider errors to human-readable flash messages.
- ✅ **Test Mode**: Use environment variables to toggle between Stripe `sk_test_...` and `sk_live_...` keys.
- ✅ **Idempotency**: Use request IDs in your webhook handlers to prevent processing the same payment twice.
