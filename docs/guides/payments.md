# Payment Integration 💳

Accept payments in your Eden application using Stripe, PayPal, and other providers. This guide covers setup, webhooks, and best practices.

## Stripe Integration

### Setup

```python
from eden import Eden
import stripe
import os

app = Eden(__name__)

# Configure Stripe
stripe.api_key = os.getenv(\"STRIPE_SECRET_KEY\")
stripe.api_version = \"2024-04-10\"

# Store publishable key for frontend
app.config.STRIPE_PUBLISHABLE_KEY = os.getenv(\"STRIPE_PUBLISHABLE_KEY\")
```

### Creating Charges

```python
@app.post(\"/charge\")
async def charge(request):
    \"\"\"Process a one-time payment.\"\"\"
    data = await request.json()
    
    try:
        charge = stripe.Charge.create(
            amount=int(data[\"amount\"] * 100),  # Amount in cents
            currency=\"usd\",
            source=data[\"token\"],
            description=data.get(\"description\", \"Payment\")
        )
        
        # Save transaction to database
        transaction = await Transaction.create(
            user_id=request.user.id,
            stripe_charge_id=charge.id,
            amount=data[\"amount\"],
            status=\"completed\"
        )
        
        return {\"charge_id\": charge.id, \"transaction_id\": transaction.id}
    
    except stripe.error.CardError as e:
        return {\"error\": e.user_message}, 400
```

### Subscriptions

```python
@app.post(\"/subscribe\")
async def create_subscription(request):
    \"\"\"Setup a recurring subscription.\"\"\"
    data = await request.json()
    user = request.user
    
    # Create or get Stripe customer
    if user.stripe_customer_id:
        customer = stripe.Customer.retrieve(user.stripe_customer_id)
    else:
        customer = stripe.Customer.create(
            email=user.email,
            name=user.name
        )
        user.stripe_customer_id = customer.id
        await user.save()
    
    # Create subscription
    subscription = stripe.Subscription.create(
        customer=customer.id,
        items=[{\"price\": data[\"price_id\"]}]
    )
    
    # Store in database
    subscription_record = await Subscription.create(
        user_id=user.id,
        stripe_subscription_id=subscription.id,
        stripe_customer_id=customer.id,
        plan=data.get(\"plan\", \"pro\"),
        status=\"active\"
    )
    
    return {\"subscription_id\": subscription_record.id}
```

### Webhooks

```python
@app.post(\"/webhooks/stripe\")
async def stripe_webhook(request):
    \"\"\"Handle Stripe webhook events.\"\"\"
    payload = await request.body()
    sig_header = request.headers.get(\"Stripe-Signature\")
    
    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            os.getenv(\"STRIPE_WEBHOOK_SECRET\")
        )
    except ValueError:
        return {\"error\": \"Invalid payload\"}, 400
    except stripe.error.SignatureVerificationError:
        return {\"error\": \"Invalid signature\"}, 400
    
    # Handle different event types
    if event[\"type\"] == \"charge.succeeded\":
        charge = event[\"data\"][\"object\"]
        transaction = await Transaction.get_by(stripe_charge_id=charge.id)
        transaction.status = \"completed\"
        await transaction.save()
    
    elif event[\"type\"] == \"charge.failed\":
        charge = event[\"data\"][\"object\"]
        transaction = await Transaction.get_by(stripe_charge_id=charge.id)
        transaction.status = \"failed\"
        await transaction.save()
    
    elif event[\"type\"] == \"customer.subscription.updated\":
        subscription = event[\"data\"][\"object\"]
        sub = await Subscription.get_by(stripe_subscription_id=subscription.id)
        sub.status = subscription.status
        await sub.save()
    
    return {\"success\": True}
```

## PayPal Integration

```python
import paypalrestsdk

paypalrestsdk.configure({
    \"mode\": \"live\",  # sandbox or live
    \"client_id\": os.getenv(\"PAYPAL_CLIENT_ID\"),
    \"client_secret\": os.getenv(\"PAYPAL_CLIENT_SECRET\")
})

@app.post(\"/paypal/charge\")
async def paypal_charge(request):
    \"\"\"Process PayPal payment.\"\"\"
    data = await request.json()
    
    payment = paypalrestsdk.Payment({
        \"intent\": \"sale\",
        \"payer\": {
            \"payment_method\": \"paypal\"
        },
        \"redirect_urls\": {
            \"return_url\": f\"{request.base_url}paypal/return\",
            \"cancel_url\": f\"{request.base_url}paypal/cancel\"
        },
        \"transactions\": [{
            \"amount\": {
                \"total\": str(data[\"amount\"]),
                \"currency\": \"USD\"
            },
            \"description\": data.get(\"description\", \"Payment\")
        }]
    })
    
    if payment.create():
        # Redirect user to approve payment
        approval_url = next(
            (link.href for link in payment.links if link.rel == \"approval_url\"),
            None
        )
        return {\"approval_url\": approval_url}
    else:
        return {\"error\": payment.error}, 400
```

## Security Best Practices

- ✅ Never expose API keys in frontend code
- ✅ Store transaction IDs in database for reconciliation
- ✅ Validate webhook signatures
- ✅ Use HTTPS for all payment endpoints
- ✅ Implement PCI compliance if storing cards
- ✅ Add rate limiting to payment endpoints
- ✅ Audit all payment transactions
- ✅ Handle refunds and disputes properly
