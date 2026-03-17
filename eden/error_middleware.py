"""
Error Handler Middleware (Layer 5)

Global exception handling middleware that:
- Catches all exceptions from routes
- Dispatches to registered error handlers
- Provides content negotiation (HTML vs JSON)
- Logs errors with context
"""

import logging
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from eden.exceptions import error_handler_registry, EdenException

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Global error handler middleware (Layer 5: Middleware Hook).
    
    Catches ALL exceptions from route handlers and dispatches them to
    the global error handler registry. Provides content negotiation
    (HTML error pages vs JSON responses).
    
    Integration with app:
        app._middleware_stack.insert(0, (ErrorHandlerMiddleware, {}))
    
    Features:
    - Catches all exceptions (Eden and non-Eden)
    - Dispatches to registered handlers
    - Content negotiation (Accept header)
    - Preserves headers from handler
    - Logs all errors
    - Admin panel gets proper error pages
    
    Example error handler flow:
        Route raises ValueError
            ↓
        ErrorHandlerMiddleware catches it
            ↓
        Queries error_handler_registry.handle_exception()
            ↓
        CustomValueErrorHandler matches, handles it
            ↓
        Returns JsonResponse with custom message
            ↓
        Middleware adds headers, sends response
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response]
    ) -> Response:
        """
        Intercept requests and catch exceptions from handler.
        
        Args:
            request: Starlette Request
            call_next: Next middleware/route handler
        
        Returns:
            Response (from handler or error handler)
        """
        try:
            response = await call_next(request)
            return response
        
        except Exception as exc:
            # Get app instance
            app = request.app
            
            # Log exception (will be re-logged by handlers if needed)
            logger.error(
                f"{type(exc).__name__} in {request.method} {request.url.path}: {exc}",
                exc_info=True
            )
            
            # Special handling for Jinja2 template errors in debug mode
            # These need the premium debug page, not the JSON fallback
            try:
                from jinja2.exceptions import TemplateError as JinjaTemplateError
                eden_app = getattr(app, "eden", app)
                if isinstance(exc, JinjaTemplateError) and getattr(eden_app, "debug", False):
                    return eden_app._render_enhanced_template_error(request, exc)
            except (ImportError, AttributeError):
                pass
            
            # Dispatch to error handler registry
            try:
                response = await error_handler_registry.handle_exception(
                    exc,
                    request,
                    app
                )
                
                # Add any custom headers from exception
                if isinstance(exc, EdenException):
                    for key, value in exc.headers.items():
                        response.headers[key] = value
                
                return response
            
            except Exception as handler_error:
                # Error handler itself failed
                logger.error(
                    f"Error handler failed: {handler_error}",
                    exc_info=True
                )
                
                # Return generic error response
                from eden.responses import JsonResponse
                return JsonResponse(
                    {
                        "error": True,
                        "detail": "Internal server error."
                    },
                    status_code=500
                )


class ContentNegotiationErrorHandler:
    """
    Mixin for error handlers that support both HTML and JSON responses.
    
    Checks Accept header and returns appropriate format:
    - Accept: application/json → JSON response
    - Accept: text/html → HTML error page
    - Default fallback
    
    Example:
        class CustomErrorHandler(ContentNegotiationErrorHandler, ErrorHandler):
            def matches(self, exc: Exception) -> bool:
                return isinstance(exc, ValueError)
            
            async def handle(self, exc: Exception, request, app):
                if self.wants_json(request):
                    return self.json_response({"error": "bad value"}, 400)
                else:
                    return self.html_response("error.html", {"error": exc}, 400)
    """

    @staticmethod
    def wants_json(request: Request) -> bool:
        """Check if client prefers JSON response (Accept header)."""
        accept = request.headers.get("accept", "text/html")
        return "application/json" in accept

    @staticmethod
    def json_response(data: dict, status_code: int = 500):
        """Create JSON error response."""
        from eden.responses import JsonResponse
        return JsonResponse(data, status_code=status_code)

    @staticmethod
    def html_response(
        template_name: str,
        context: dict,
        status_code: int = 500,
        app=None
    ):
        """
        Create HTML error response from template.
        
        Args:
            template_name: Template filename (e.g., "error_500.html")
            context: Template context variables
            status_code: HTTP status code
            app: Eden application (gets from context if not provided)
        
        Returns:
            HtmlResponse with rendered template
        """
        from eden.responses import HtmlResponse
        from eden.context import get_app
        
        if app is None:
            app = get_app()
        
        # Add default context
        context.setdefault("status_code", status_code)
        context.setdefault("title", f"Error {status_code}")
        
        try:
            html = app.templates.get_template(template_name).render(**context)
            return HtmlResponse(html, status_code=status_code)
        except Exception as e:
            logger.error(f"Failed to render error template {template_name}: {e}")
            # Fallback to JSON
            return ContentNegotiationErrorHandler.json_response(
                {
                    "error": True,
                    "status_code": status_code,
                    "detail": context.get("detail", "An error occurred")
                },
                status_code
            )
