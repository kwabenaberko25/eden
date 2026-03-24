"""
Eden — Payment Webhooks

Event-driven webhook handler with deduplication and signature verification.
"""

import logging
from collections.abc import Callable

from eden.requests import Request
from eden.responses import JsonResponse

logger = logging.getLogger("eden.payments")


class WebhookRouter:
    """
    Routes webhook events from payment providers to handler functions.

    Usage:
        from eden.payments import WebhookRouter

        webhooks = WebhookRouter()

        @webhooks.on("checkout.session.completed")
        async def handle_checkout(event_data: dict):
            # Process the checkout completion
            ...

        @webhooks.on("customer.subscription.updated")
        async def handle_sub_update(event_data: dict):
            ...

        # Mount in your app:
        app.mount_webhooks("/webhooks/stripe", webhooks)
    """

    def __init__(self):
        self._handlers: dict[str, list[Callable]] = {}

    def on(self, event_type: str) -> Callable:
        """Decorator to register a handler for a specific event type."""

        def decorator(func: Callable) -> Callable:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(func)
            return func

        return decorator

    async def dispatch(self, event_type: str, event_data: dict) -> bool:
        """
        Dispatch an event to all registered handlers.
        Returns True if all handlers completed without unhandled exceptions.
        """
        handlers = self._handlers.get(event_type, [])
        if not handlers:
            logger.info(f"No handler for event type: {event_type}")
            return True

        all_success = True
        for handler in handlers:
            try:
                result = handler(event_data)
                # Support both sync and async handlers
                if hasattr(result, "__await__"):
                    await result
            except Exception as e:
                logger.error(f"Error in webhook handler for {event_type}: {e}")
                all_success = False
        
        return all_success

    def build_route(self, path: str = "/webhooks/stripe"):
        """
        Build a Starlette Route for handling incoming webhooks.
        """
        from starlette.routing import Route

        router_ref = self

        async def webhook_endpoint(request: Request) -> JsonResponse:
            """Handle incoming webhook from payment provider."""
            from eden.payments.models import PaymentEvent

            body = await request.body()
            signature = request.headers.get("stripe-signature", "")

            # Get provider from app
            provider = getattr(request.app, "payments", None)
            if not provider:
                return JsonResponse({"error": "No payment provider configured"}, status_code=500)

            # Verify signature
            try:
                event = provider.verify_webhook_signature(body, signature)
            except Exception as e:
                logger.warning(f"Webhook signature verification failed: {e}")
                return JsonResponse({"error": "Invalid signature"}, status_code=400)

            event_id = event.get("id", "")
            event_type = event.get("type", "")
            event_data = event.get("data", {}).get("object", {})

            # Deduplication — check if already processed
            session = getattr(request.state, "db", None)
            if not session:
                return JsonResponse({"error": "No database session available"}, status_code=500)

            # Use Model._get_db() to get the database instance
            from eden.payments.models import PaymentEvent
            db = PaymentEvent._get_db()
            
            async with db.transaction(session=session) as tx_session:
                from sqlalchemy import select
                existing = await tx_session.execute(
                    select(PaymentEvent).where(PaymentEvent.provider_event_id == event_id)
                )
                if existing.scalar_one_or_none():
                    return JsonResponse({"status": "already_processed"})

                # Store event
                payment_event = PaymentEvent(
                    provider_event_id=event_id,
                    event_type=event_type,
                    payload=event,
                )
                tx_session.add(payment_event)
                await tx_session.flush()

                # Dispatch to handlers
                # Note: Handlers should ideally share the same transaction, or start their own savepoints
                success = await router_ref.dispatch(event_type, event_data)

                # Mark as processed only if all handlers succeeded
                if success:
                    payment_event.processed = True
                    await tx_session.flush()
                else:
                    # Log failure but return 200/OK to prevent Stripe from bombarding us immediately
                    # Standard practice is to mark as failure/retry-later if needed, but since we 
                    # didn't set 'processed', the next attempt from Stripe will try again.
                    # We return 500 to signal failure to Stripe so they retry.
                    return JsonResponse({"status": "handler_failed"}, status_code=500)

            return JsonResponse({"status": "ok"})

        return Route(path, webhook_endpoint, methods=["POST"])
