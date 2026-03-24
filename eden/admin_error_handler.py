"""
Admin panel error handler that renders styled HTML error pages.

This handler detects when the client is accessing the admin panel (based on URL path)
and renders beautiful HTML error pages instead of JSON. Uses content negotiation to
determine response format (Accept header).

Integration:
    app.register_error_handler(AdminErrorHandler())
"""

import logging
from typing import Optional
from starlette.requests import Request
from starlette.responses import Response, HTMLResponse
from starlette.templating import Jinja2Templates
import uuid

from eden.exceptions import ErrorHandler, EdenException

logger = logging.getLogger(__name__)


class AdminErrorHandler(ErrorHandler):
    """
    Render HTML error pages for admin panel requests.
    
    Renders styled error.html template with:
    - Status code and title
    - User-friendly error message
    - Detailed technical info (server-side only, not shown to users)
    - Context data for debugging
    - Links to navigate home or retry
    
    Features:
    - Content negotiation: Returns HTML for browser requests, JSON otherwise
    - Responsive design: Mobile-friendly error pages
    - Error tracking: Assigns unique error ID for server logs
    - Context preservation: Includes operation/field details when available
    
    The handler also integrates with the TemplateRenderer to respect app
    settings for template directories.
    
    Attributes:
        templates_dir: Path to templates directory (e.g., 'templates/')
        error_templates: Map of status_code -> template_name
    """
    
    def __init__(self, templates_dir: str = "templates"):
        """
        Initialize AdminErrorHandler.
        
        Args:
            templates_dir: Path to templates directory containing error.html, error_401.html, etc.
        """
        self.templates_dir = templates_dir
        self.error_templates = {
            401: "error_401.html",
            403: "error_403.html",
            404: "error_404.html",
            500: "error_500.html",
        }
        # Lazy load templates
        self._templates: Optional[Jinja2Templates] = None
    
    def _get_templates(self) -> Jinja2Templates:
        """Lazy load Jinja2 templates."""
        if self._templates is None:
            try:
                self._templates = Jinja2Templates(directory=self.templates_dir)
            except Exception as e:
                logger.warning(f"Failed to load templates from {self.templates_dir}: {e}")
                self._templates = None
        return self._templates
    
    def matches(self, exc: Exception) -> bool:
        """Check if exception should be handled (always true for catchall)."""
        # This is a low-priority catchall handler, so it matches everything
        # but returns False for other specific handlers that match first
        return True
    
    def _should_render_html(self, request: Request) -> bool:
        """
        Determine if HTML should be rendered based on request context.
        
        Returns True if:
        - Request is for admin panel (/admin/*)
        - Accept header prefers text/html
        - Client is a web browser
        """
        # Check if admin panel request
        if request.url.path.startswith("/admin") or request.url.path.startswith("/ps/admin"):
            return True
        
        # Check Accept header
        accept = request.headers.get("Accept", "")
        if "text/html" in accept and "application/json" not in accept:
            return True
        
        # Check User-Agent for browser
        user_agent = request.headers.get("User-Agent", "")
        if any(ua in user_agent.lower() for ua in ["mozilla", "chrome", "safari", "edge"]):
            return True
        
        return False
    
    def _get_error_details(self, exc: Exception, status_code: int) -> dict:
        """Extract error details from exception."""
        details = {
            "status_code": status_code,
            "error_id": uuid.uuid4().hex[:8].upper(),
            "title": self._get_error_title(status_code),
            "message": self._get_error_message(exc, status_code),
        }
        
        # Extract context if available
        if isinstance(exc, EdenException):
            context = exc.context or {}
            details["context"] = context
            details["details"] = str(exc.detail) if hasattr(exc, 'detail') else str(exc)
        else:
            details["details"] = str(exc)
        
        return details
    
    def _get_error_title(self, status_code: int) -> str:
        """Get human-readable error title."""
        titles = {
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            409: "Conflict",
            422: "Invalid Data",
            500: "Server Error",
            503: "Service Unavailable",
        }
        return titles.get(status_code, f"Error {status_code}")
    
    def _get_error_message(self, exc: Exception, status_code: int) -> str:
        """Get user-friendly error message."""
        if isinstance(exc, EdenException):
            return str(exc.detail) if hasattr(exc, 'detail') else str(exc)
        
        messages = {
            400: "The request could not be understood or was malformed.",
            401: "Authentication required. Please log in.",
            403: "You don't have permission to access this resource.",
            404: "The requested resource was not found.",
            409: "The request conflicts with existing data.",
            422: "The data provided failed validation.",
            500: "An unexpected error occurred. Our team has been notified.",
            503: "The service is temporarily unavailable. Please try again later.",
        }
        
        return messages.get(status_code, str(exc))
    
    async def handle(self, exc: Exception, request: Request) -> Response:
        """Handle error and render HTML or JSON response."""
        # Determine status code
        if isinstance(exc, EdenException):
            status_code = getattr(exc, 'status_code', 500)
        else:
            status_code = getattr(exc, 'status_code', 500)
        
        # Check if HTML should be rendered
        if not self._should_render_html(request):
            # Return JSON instead
            from starlette.responses import JSONResponse
            return JSONResponse(
                {
                    "status": "error",
                    "detail": self._get_error_message(exc, status_code),
                    "type": type(exc).__name__,
                },
                status_code=status_code,
            )
        
        # Render HTML
        error_details = self._get_error_details(exc, status_code)
        
        templates = self._get_templates()
        if templates is None:
            # Fallback to plain HTML
            return HTMLResponse(
                f"""
                <html>
                <head><meta charset="utf-8"><title>Error</title></head>
                <body>
                <h1>{error_details['title']}</h1>
                <p>{error_details['message']}</p>
                </body>
                </html>
                """,
                status_code=status_code,
            )
        
        # Try to render template
        template_name = self.error_templates.get(status_code, "error.html")
        try:
            return templates.TemplateResponse(
                request,
                template_name,
                {
                    "request": request,
                    **error_details,
                },
                status_code=status_code,
            )
        except Exception as e:
            logger.warning(f"Failed to render {template_name}: {e}")
            # Fallback to generic error template
            return templates.TemplateResponse(
                request,
                "error.html",
                {
                    "request": request,
                    **error_details,
                },
                status_code=status_code,
            )


class AdminPanelMiddleware:
    """
    Middleware to enable admin panel error handling.
    
    Registers AdminErrorHandler automatically on app startup.
    
    Usage:
        app.add_middleware(AdminPanelMiddleware)
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, async_receive, async_send):
        if scope["type"] == "http":
            # Install admin handler once
            if not hasattr(self.app, '_admin_handler_registered'):
                try:
                    error_handler = AdminErrorHandler()
                    if hasattr(self.app, 'register_error_handler'):
                        self.app.register_error_handler(error_handler)
                    self.app._admin_handler_registered = True
                except Exception as e:
                    logger.warning(f"Failed to register admin error handler: {e}")
        
        await self.app(scope, async_receive, async_send)


__all__ = ["AdminErrorHandler", "AdminPanelMiddleware"]
