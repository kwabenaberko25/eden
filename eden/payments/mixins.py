from typing import Any, Optional
from eden.db import f


class BillingManager:
    """
    High-level manager for billing operations on a model instance.
    """

    def __init__(self, instance: Any):
        self.instance = instance

    def _get_provider(self):
        from eden.context import request
        try:
            return request.app.payments
        except Exception:
            raise RuntimeError(
                "Billing operations require an active request context "
                "with a payment provider configured."
            )

    async def create_checkout_session(
        self, 
        plan_id: str, 
        success_url: str = "/", 
        cancel_url: str = "/",
        **kwargs
    ) -> str:
        """
        Create a checkout session for this user.
        """
        provider = self._get_provider()
        
        # Ensure customer exists in provider
        customer_id = self.instance.stripe_customer_id
        if not customer_id:
            customer_id = await provider.create_customer(
                email=getattr(self.instance, "email", ""),
                name=getattr(self.instance, "name", ""),
            )
            self.instance.stripe_customer_id = customer_id
            await self.instance.save()
            
        return await provider.create_checkout_session(
            customer_id=customer_id,
            price_id=plan_id,
            success_url=success_url,
            cancel_url=cancel_url,
            **kwargs
        )

    async def create_portal_session(self, return_url: str = "/") -> str:
        """
        Create a billing portal session for this user.
        """
        provider = self._get_provider()
        customer_id = self.instance.stripe_customer_id
        if not customer_id:
            raise ValueError("Customer has no billing history.")
            
        return await provider.create_portal_session(
            customer_id=customer_id,
            return_url=return_url
        )


from sqlalchemy.orm import Mapped

class CustomerMixin:
    """
    Adds Stripe customer integration to an Eden Model.
    Typically used on the User or Organization model.
    """
    stripe_customer_id: Mapped[Optional[str]] = f(max_length=255, nullable=True, index=True)
    
    @property
    def billing(self) -> BillingManager:
        """Access high-level billing operations."""
        return BillingManager(self)

    async def is_subscribed(self) -> bool:
        """
        Check if this customer has an active subscription in the database.
        """
        if not self.stripe_customer_id:
            return False

        from eden.payments.models import Customer, Subscription
        from eden.db import Q

        try:
            # First, find the Customer record to get its primary key
            customer = await Customer.filter(provider_customer_id=self.stripe_customer_id).first()
            if not customer:
                return False

            # Check for active or trialing subscriptions
            # We use Q to support multiple active statuses
            has_active = await Subscription.filter(
                Q(customer_id=customer.id) & 
                Q(status__in=["active", "trialing"])
            ).exists()
            
            return has_active
        except Exception:
            # Fallback if payments models aren't migrated or available
            return False

    def __repr__(self) -> str:
        return f"<Customer(stripe_id='{self.stripe_customer_id}')>"
