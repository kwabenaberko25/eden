from eden.db import f

class CustomerMixin:
    """
    Adds Stripe customer integration to an Eden Model.
    Typically used on the User or Organization model.
    """
    stripe_customer_id: str | None = f(max_length=255, nullable=True, index=True)
    
    @property
    def is_subscribed(self) -> bool:
        """Helper to check if this entity has an active subscription."""
        return False

    def __repr__(self) -> str:
        return f"<CustomerMixin(stripe_id='{self.stripe_customer_id}')>"
