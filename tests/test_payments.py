"""
Eden — Payment Tests

Tests for PaymentProvider, WebhookRouter, models, and mixins.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock

from eden.payments.providers import PaymentProvider
from eden.payments.webhooks import WebhookRouter
from eden.payments.mixins import CustomerMixin


# ── PaymentProvider Tests ─────────────────────────────────────────────


class TestPaymentProvider:
    """Tests for the abstract PaymentProvider."""

    def test_cannot_instantiate_abstract(self):
        """PaymentProvider should not be directly instantiatable."""
        with pytest.raises(TypeError):
            PaymentProvider()


# ── WebhookRouter Tests ──────────────────────────────────────────────


class TestWebhookRouter:
    """Tests for the webhook event routing system."""

    def test_register_handler(self):
        router = WebhookRouter()

        @router.on("checkout.session.completed")
        async def handle_checkout(data):
            pass

        assert "checkout.session.completed" in router._handlers
        assert len(router._handlers["checkout.session.completed"]) == 1

    def test_register_multiple_handlers(self):
        router = WebhookRouter()

        @router.on("customer.subscription.updated")
        async def handler1(data):
            pass

        @router.on("customer.subscription.updated")
        async def handler2(data):
            pass

        assert len(router._handlers["customer.subscription.updated"]) == 2

    @pytest.mark.asyncio
    async def test_dispatch(self):
        router = WebhookRouter()
        received = []

        @router.on("test.event")
        async def handler(data):
            received.append(data)

        await router.dispatch("test.event", {"key": "value"})
        assert received == [{"key": "value"}]

    @pytest.mark.asyncio
    async def test_dispatch_no_handler(self):
        """Dispatching an unregistered event should not raise."""
        router = WebhookRouter()
        await router.dispatch("unknown.event", {})

    @pytest.mark.asyncio
    async def test_dispatch_multiple_handlers(self):
        router = WebhookRouter()
        results = []

        @router.on("multi.event")
        async def handler1(data):
            results.append("h1")

        @router.on("multi.event")
        async def handler2(data):
            results.append("h2")

        await router.dispatch("multi.event", {})
        assert results == ["h1", "h2"]


# ── CustomerMixin Tests ──────────────────────────────────────────────


class TestCustomerMixin:
    """Tests for the CustomerMixin methods."""

    @pytest.mark.asyncio
    async def test_is_subscribed_default(self):
        """Default is_subscribed should return False."""

        class MockUser(CustomerMixin):
            id = "user-123"

        user = MockUser()
        assert await user.is_subscribed() is False
