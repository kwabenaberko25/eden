"""
Eden — Context Middleware (Layer 2)

ASGI middleware that automatically manages request context lifecycle.

Responsibilities:
- Call context_manager.on_request_start() before routing
- Ensure context_manager.on_request_end() is called in finally block
- Prevent context leaks due to exceptions or early returns
- Work with async/concurrent requests (each has isolated context)

Integration:
    # In app.py startup:
    from eden.context_middleware import ContextMiddleware
    
    app.add_middleware(ContextMiddleware)  # Must be OUTER middleware
    
Design:
- Wraps request/response cycle
- Uses try/finally to guarantee cleanup
- Does NOT interfere with exception handling (errors propagate)
- Thread-safe and async-safe via ContextVars

Important:
- Must be registered EARLY in middleware stack (before auth, tenancy, etc.)
- Does NOT require manual setup by developers
"""

from __future__ import annotations

import logging
from typing import Callable, TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from eden.context import context_manager

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response

logger = logging.getLogger(__name__)


class ContextMiddleware(BaseHTTPMiddleware):
    """
    ASGI middleware for automatic context lifecycle management.

    Automatically initializes context at request start and cleans up at request end.
    Ensures all request-scoped data (user, tenant, request_id) is isolated per request.

    Usage:
        # In Eden app startup
        from eden.context_middleware import ContextMiddleware
        from eden.app import Eden
        
        app = Eden()
        app.add_middleware(ContextMiddleware)
        
        # In request handlers, context is ready to use:
        @app.get("/users")
        async def list_users(request: Request):
            user = get_user()  # Auto-available
            request_id = get_request_id()  # For logging
            return {"users": [...]}

    Lifecycle:
        1. Request arrives
        2. on_request_start(request, app) → Initialize context
        3. Route handler executes (context available)
        4. Response ready
        5. on_request_end() → Cleanup (in finally block)
        6. Response sent
    """

    async def dispatch(self, request: "Request", call_next: Callable) -> "Response":
        """
        Process request with automatic context setup/teardown.

        Args:
            request: Starlette Request
            call_next: Next middleware/handler callable

        Returns:
            Response (status, headers, body)

        Implementation Notes:
            - Initializes context before call_next
            - Ensures cleanup in try/finally (never leaks context)
            - Does NOT catch exceptions (lets error handlers deal with them)
            - Each concurrent request has isolated context via ContextVars
        """
        try:
            # Initialize context at request start
            # app is accessible via request.app
            await context_manager.on_request_start(request, request.app)

            # Call next middleware/handler
            # This is where route handlers run and can access context
            response = await call_next(request)

            return response

        finally:
            # ALWAYS cleanup, even if exception occurred
            # This is critical to prevent context leaks
            await context_manager.on_request_end()
