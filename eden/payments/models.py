"""
Eden — Payment Models

Database models for customers, subscriptions, and payment events.
"""

import datetime
import uuid

from sqlalchemy import JSON
from sqlalchemy.orm import mapped_column

from eden.db import Model, f


class Customer(Model):
    """
    Links a user to their payment provider's customer account.

    Tablename: eden_customers
    """

    __tablename__ = "eden_customers"

    user_id: uuid.UUID = f(foreign_key="eden_users.id", unique=True)
    provider_customer_id: str = f(unique=True, index=True)
    provider: str = f(max_length=50, default="stripe")

    def __repr__(self) -> str:
        return f"<Customer(provider={self.provider}, customer_id={self.provider_customer_id})>"


class Subscription(Model):
    """
    Tracks a customer's subscription.

    Tablename: eden_subscriptions
    """

    __tablename__ = "eden_subscriptions"

    customer_id: uuid.UUID = f(foreign_key="eden_customers.id", index=True)
    provider_subscription_id: str = f(unique=True, index=True)
    status: str = f(max_length=50, default="active")
    price_id: str | None = f(max_length=255, nullable=True)
    current_period_end: datetime.datetime | None = f(nullable=True)
    cancel_at_period_end: bool = f(default=False)

    @property
    def is_active(self) -> bool:
        """Check if subscription is in an active state."""
        return self.status in ("active", "trialing")

    def __repr__(self) -> str:
        return f"<Subscription(status={self.status}, price={self.price_id})>"


class PaymentEvent(Model):
    """
    Stores raw webhook events for idempotency and audit.

    Tablename: eden_payment_events
    """

    __tablename__ = "eden_payment_events"

    provider_event_id: str = f(unique=True, index=True)
    event_type: str = f(max_length=255, index=True)
    payload: dict = mapped_column(JSON, default=dict)
    processed: bool = f(default=False)

    def __repr__(self) -> str:
        return f"<PaymentEvent(type={self.event_type}, processed={self.processed})>"
