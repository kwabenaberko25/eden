"""
Eden — Payment Providers

Abstract payment provider interface and Stripe implementation.
"""

from abc import ABC, abstractmethod


class PaymentProvider(ABC):
    """
    Abstract base for payment providers.

    All provider-specific logic is encapsulated here, keeping
    application code provider-agnostic.
    """

    @abstractmethod
    async def create_customer(
        self, email: str, name: str = "", metadata: dict = None
    ) -> str:
        """Create a customer in the payment provider. Returns provider customer ID."""
        ...

    @abstractmethod
    async def create_checkout_session(
        self,
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
        mode: str = "subscription",
        metadata: dict = None,
    ) -> str:
        """Create a checkout session. Returns checkout URL."""
        ...

    @abstractmethod
    async def create_portal_session(
        self, customer_id: str, return_url: str
    ) -> str:
        """Create a billing portal session. Returns portal URL."""
        ...

    @abstractmethod
    async def cancel_subscription(self, subscription_id: str) -> bool:
        """Cancel a subscription. Returns True on success."""
        ...

    @abstractmethod
    async def get_subscription(self, subscription_id: str) -> dict:
        """Retrieve subscription details."""
        ...

    @abstractmethod
    def verify_webhook_signature(self, payload: bytes, signature: str) -> dict:
        """Verify and parse a webhook payload. Returns the event dict."""
        ...


class StripeProvider(PaymentProvider):
    """
    Stripe payment provider.

    Requires: `uv add stripe` or `pip install stripe`

    Usage:
        from eden.payments import StripeProvider

        provider = StripeProvider(
            api_key="sk_...",
            webhook_secret="whsec_...",
        )
        app.configure_payments(provider)
    """

    def __init__(
        self,
        api_key: str,
        webhook_secret: str = "",
        api_version: str = "2024-12-18.acacia",
    ):
        try:
            import stripe
        except ImportError:
            raise ImportError(
                "stripe is required for StripeProvider. "
                "Install it with: uv add stripe"
            )

        self.api_key = api_key
        self.webhook_secret = webhook_secret
        stripe.api_key = api_key
        stripe.api_version = api_version
        self._stripe = stripe

    async def create_customer(
        self, email: str, name: str = "", metadata: dict = None
    ) -> str:
        customer = self._stripe.Customer.create(
            email=email,
            name=name or None,
            metadata=metadata or {},
        )
        return customer.id

    async def create_checkout_session(
        self,
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
        mode: str = "subscription",
        metadata: dict = None,
    ) -> str:
        session = self._stripe.checkout.Session.create(
            customer=customer_id,
            line_items=[{"price": price_id, "quantity": 1}],
            mode=mode,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata or {},
        )
        return session.url

    async def create_portal_session(
        self, customer_id: str, return_url: str
    ) -> str:
        session = self._stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        return session.url

    async def cancel_subscription(self, subscription_id: str) -> bool:
        try:
            self._stripe.Subscription.cancel(subscription_id)
            return True
        except Exception:
            return False

    async def get_subscription(self, subscription_id: str) -> dict:
        sub = self._stripe.Subscription.retrieve(subscription_id)
        return {
            "id": sub.id,
            "status": sub.status,
            "current_period_end": sub.current_period_end,
            "cancel_at_period_end": sub.cancel_at_period_end,
        }

    def verify_webhook_signature(self, payload: bytes, signature: str) -> dict:
        event = self._stripe.Webhook.construct_event(
            payload, signature, self.webhook_secret
        )
        return dict(event)
