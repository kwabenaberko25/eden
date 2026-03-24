"""
Eden — Payments Package

Billing, subscriptions, and payment provider integration.
"""

from eden.payments.mixins import CustomerMixin
from eden.payments.models import Customer, PaymentEvent, Subscription
from eden.payments.providers import PaymentProvider, StripeProvider
from eden.payments.webhooks import WebhookRouter

# --- Simplified Stripe API ---
import functools
from typing import Any, Callable

class StripeClientProxy:
    """Proxy to Stripe SDK for async usage in Eden."""
    def __getattr__(self, name: str) -> Any:
        import stripe
        return getattr(stripe, name)

stripe_client = StripeClientProxy()

def stripe_webhook(func: Callable) -> Callable:
    """Decorator to mark a view as a Stripe webhook handler."""
    @functools.wraps(func)
    async def wrapper(request, *args, **kwargs):
        return await func(request, *args, **kwargs)
    return wrapper

__all__ = [
    "PaymentProvider",
    "StripeProvider",
    "Customer",
    "Subscription",
    "PaymentEvent",
    "CustomerMixin",
    "WebhookRouter",
    "stripe_client",
    "stripe_webhook",
]
