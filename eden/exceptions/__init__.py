"""
Eden — Exception Classes & Error Handler System

Structured error handling with:
- Exception classes with context support
- Global error handler registry (plugin system)
- Automatic JSON/HTML error responses
- Chainable error handlers for customization
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional

from eden.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_405_METHOD_NOT_ALLOWED,
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_429_TOO_MANY_REQUESTS,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

logger = logging.getLogger(__name__)


class EdenException(Exception):
    """
    Base exception for all Eden errors.
    
    Features:
    - Automatic JSON serialization
    - HTTP status code mapping
    - Custom headers support
    - Additional context (extra data)
    - Logging support
    
    Example:
        raise EdenException(
            detail="User not found",
            status_code=404,
            extra={"user_id": 123}
        )
    """

    status_code: int = HTTP_500_INTERNAL_SERVER_ERROR
    detail: str = "An unexpected error occurred."

    def __init__(
        self,
        detail: str | None = None,
        status_code: int | None = None,
        headers: dict[str, str] | None = None,
        extra: dict[str, Any] | None = None,
        context: dict[str, str] | None = None,
    ) -> None:
        """
        Initialize exception with optional customization.
        
        Args:
            detail: User-facing error message
            status_code: HTTP status code
            headers: Custom HTTP headers to include in response
            extra: Additional JSON-serializable data
            context: Internal debugging context (operation, resource, suggestion)
        
        Implementation Notes:
            - context is for internal logging only (not shown to users)
            - detail should be user-friendly and non-technical
            - status_code defaults to class definition
        """
        if detail is not None:
            self.detail = detail
        if status_code is not None:
            self.status_code = status_code
        self.headers = headers or {}
        self.extra = extra or {}
        self.context = context or {}
        super().__init__(self.detail)

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize exception to a JSON-friendly dictionary.
        
        Returns:
            Dict with error, status_code, detail, and extra fields
            (context is excluded from response for security)
        """
        result: dict[str, Any] = {
            "error": True,
            "status_code": self.status_code,
            "detail": self.detail,
        }
        if self.extra:
            result["extra"] = self.extra
        return result

    def log_context(self) -> None:
        """
        Log detailed context information (for server-side debugging).
        
        Called by error handler middleware before sending response to user.
        Logs full context while user sees friendly message.
        """
        if self.context:
            logger.error(
                f"{self.__class__.__name__} with context: {self.context}"
            )


class HttpException(EdenException):
    """General HTTP exception with a specific status code."""

    pass


class BadRequest(EdenException):
    """400 Bad Request."""

    status_code = HTTP_400_BAD_REQUEST
    detail = "Bad request."


class Unauthorized(EdenException):
    """401 Unauthorized."""

    status_code = HTTP_401_UNAUTHORIZED
    detail = "Authentication required."


class Forbidden(EdenException):
    """403 Forbidden."""

    status_code = HTTP_403_FORBIDDEN
    detail = "Permission denied."


class PermissionDenied(Forbidden):
    """
    Permission denied — user lacks required permissions or roles.
    Alias/subclass of Forbidden for more explicit error handling.
    """

    detail = "Permission denied."


class NotFound(EdenException):
    """404 Not Found."""

    status_code = HTTP_404_NOT_FOUND
    detail = "Resource not found."


class MethodNotAllowed(EdenException):
    """405 Method Not Allowed."""

    status_code = HTTP_405_METHOD_NOT_ALLOWED
    detail = "Method not allowed."


class Conflict(EdenException):
    """409 Conflict."""

    status_code = HTTP_409_CONFLICT
    detail = "Resource conflict."


class ValidationError(EdenException):
    """422 Unprocessable Entity — request body validation failed."""

    status_code = HTTP_422_UNPROCESSABLE_ENTITY
    detail = "Validation error."

    def __init__(
        self,
        errors: list[dict[str, Any]] | None = None,
        detail: str | None = None,
        **kwargs: Any,
    ) -> None:
        self.errors = errors or []
        super().__init__(detail=detail, extra={"errors": self.errors}, **kwargs)


class TooManyRequests(EdenException):
    """429 Too Many Requests."""

    status_code = HTTP_429_TOO_MANY_REQUESTS
    detail = "Too many requests. Please slow down."


class InternalServerError(EdenException):
    """500 Internal Server Error."""

    status_code = HTTP_500_INTERNAL_SERVER_ERROR
    detail = "Internal server error."


class EdenDatabaseError(EdenException):
    """
    Wraps raw database/ORM exceptions into a structured Eden error.

    Provides diagnostic context (operation, model) while hiding
    raw SQLAlchemy internals from API callers.

    Attributes:
        operation: The ORM operation that failed (e.g., "bulk_create", "save")
        model_name: The model class name involved
        original: The original database exception (also chained via __cause__)

    Example:
        try:
            await User.bulk_create([...])
        except EdenDatabaseError as e:
            print(e.operation)    # "bulk_create"
            print(e.model_name)   # "User"
            print(e.original)     # IntegrityError(...)
    """

    status_code = HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(
        self,
        detail: str = "A database operation failed.",
        *,
        operation: str = "",
        model_name: str = "",
        original: Exception | None = None,
        **kwargs: Any,
    ) -> None:
        self.operation = operation
        self.model_name = model_name
        self.original = original
        super().__init__(
            detail=detail,
            context={
                "operation": operation,
                "model": model_name,
                "original_error": repr(original) if original else "",
            },
            **kwargs,
        )


class EdenTemplateRecursionError(EdenException):
    """
    Raised when template nesting depth exceeds the configured limit.

    This prevents stack overflows from maliciously or accidentally self-including
    templates, deeply nested directive blocks, or recursive macro expansions.

    Attributes:
        max_depth: The maximum allowed nesting depth
        template_name: The template being processed when the limit was hit
        line: The source line number where the recursion was detected

    Example:
        try:
            parser.parse()
        except EdenTemplateRecursionError as e:
            print(e.max_depth)       # 100
            print(e.template_name)   # "partials/sidebar.html"
            print(e.detail)          # "Maximum template nesting depth exceeded (max 100)."
    """

    status_code = HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(
        self,
        detail: str = "Maximum template nesting depth exceeded.",
        *,
        max_depth: int = 0,
        template_name: str = "",
        line: int = 0,
        column: int = 0,
        **kwargs: Any,
    ) -> None:
        self.max_depth = max_depth
        self.template_name = template_name
        self.line = line
        self.column = column
        super().__init__(
            detail=detail,
            context={
                "max_depth": max_depth,
                "template_name": template_name,
                "line": line,
                "column": column,
            },
            **kwargs,
        )


class EdenTemplateResourceError(EdenException):
    """
    Raised when a template loop exceeds the configured iteration limit.

    This prevents DoS attacks via infinite or excessively long loops in
    user-controlled template content. The iteration limit is configurable
    but defaults to 10,000.

    Attributes:
        max_iterations: The maximum allowed loop iterations
        template_name: The template where the limit was hit
        line: The source line number of the loop directive

    Example:
        # In a template: @for(i in range(100000)) { ... }
        # At runtime, the loop breaks after MAX_LOOP_ITERATIONS
    """

    status_code = HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(
        self,
        detail: str = "Template loop iteration limit exceeded.",
        *,
        max_iterations: int = 0,
        template_name: str = "",
        line: int = 0,
        **kwargs: Any,
    ) -> None:
        self.max_iterations = max_iterations
        self.template_name = template_name
        self.line = line
        super().__init__(
            detail=detail,
            context={
                "max_iterations": max_iterations,
                "template_name": template_name,
                "line": line,
            },
            **kwargs,
        )


# ────────────────────────────────────────────────────────────────────────────
# Global Error Handler System (Layer 5-6)
# ────────────────────────────────────────────────────────────────────────────


class ErrorHandler(ABC):
    """
    Abstract base class for error handlers (Layer 6: Plugin system).
    
    Error handlers are registered globally and can:
    - Catch specific exception types
    - Transform exceptions before sending to user
    - Customize status codes, messages, templates
    - Handle chaining (pass to next handler)
    
    Example:
        class DatabaseErrorHandler(ErrorHandler):
            def matches(self, exc: Exception) -> bool:
                return isinstance(exc, DatabaseException)
            
            async def handle(self, exc: Exception, request, app):
                # Log database error details
                logger.error(f"Database error: {exc}")
                
                # Return user-friendly response
                return JsonResponse(
                    {
                        "error": True,
                        "detail": "Database operation failed. Please try again later."
                    },
                    status_code=500
                )
        
        app.register_error_handler(DatabaseErrorHandler())
    """

    def _is_json_request(self, request) -> bool:
        """Check if the request prefers a JSON response."""
        accept = request.headers.get("accept", "").lower()
        content_type = request.headers.get("content-type", "").lower()
        return "application/json" in accept or "application/json" in content_type

    @abstractmethod
    async def handle(self, exc: Exception, request, app):
        """
        Handle the exception and return a response.
        
        Args:
            exc: Exception to handle
            request: Starlette Request object
            app: Eden application instance
        
        Returns:
            A Starlette Response object (HTML, JSON, or custom)
        
        Raises:
            Exception: Can re-raise or raise different exception
                      (will be passed to next handler or default handler)
        """
        pass


class DefaultErrorHandler(ErrorHandler):
    """
    Default error handler for unhandled exceptions.
    
    Falls back to this when no other handler matches.
    Converts EdenException to JSON response.
    """

    def matches(self, exc: Exception) -> bool:
        """Matches all exceptions (fallback)."""
        return True

    def _should_render_html(self, request, app) -> bool:
        """Check if we should render the high-fidelity HTML debug page."""
        return app.debug and not self._is_json_request(request)

    async def handle(self, exc: Exception, request, app):
        """Convert exception to JSON response."""
        from eden.responses import JsonResponse

        # Log context if available
        if isinstance(exc, EdenException):
            exc.log_context()
            if self._should_render_html(request, app):
                return app._render_enhanced_exception(request, exc)
            return JsonResponse(exc.to_dict(), status_code=exc.status_code)

        # Fallback for Starlette HTTPException or any object with status_code
        status_code = getattr(exc, "status_code", None)
        detail = getattr(exc, "detail", None) or str(exc)
        if status_code is not None:
             if self._should_render_html(request, app):
                 return app._render_enhanced_exception(request, exc)
             return JsonResponse(
                {
                    "error": True,
                    "status_code": status_code,
                    "detail": detail
                },
                status_code=status_code
            )
        
        # For non-Eden exceptions, return generic error
        logger.error(f"Unhandled non-Eden exception: {type(exc).__name__}: {exc}", exc_info=True)
        return JsonResponse(
            {
                "error": True,
                "status_code": HTTP_500_INTERNAL_SERVER_ERROR,
                "detail": "Internal server error."
            },
            status_code=HTTP_500_INTERNAL_SERVER_ERROR
        )


class StarletteHTTPErrorHandler(ErrorHandler):
    """
    Handler for Starlette's built-in HTTPException (404, 405, etc).
    """

    def matches(self, exc: Exception) -> bool:
        from starlette.exceptions import HTTPException as StarletteHTTPException
        if isinstance(exc, StarletteHTTPException):
            return True
        return hasattr(exc, "status_code") and hasattr(exc, "detail") and not isinstance(exc, EdenException)

    def _should_render_html(self, request, app) -> bool:
        """Check if we should render the high-fidelity HTML debug page."""
        return app.debug and not self._is_json_request(request)

    async def handle(self, exc: Exception, request, app):
        from eden.responses import JsonResponse
        # exc is known to be StarletteHTTPException here (or have equivalent attributes)
        status_code = getattr(exc, "status_code", 500)
        detail = getattr(exc, "detail", None) or str(exc)
        
        if self._should_render_html(request, app):
            return app._render_enhanced_exception(request, exc)
            
        return JsonResponse(
            {
                "error": True,
                "status_code": status_code,
                "detail": detail
            },
            status_code=status_code
        )


class ErrorHandlerRegistry:
    """
    Global registry for error handlers (Layer 5: Middleware hook).
    
    Manages a list of handlers and dispatches exceptions to them in order.
    First matching handler handles the exception.
    
    Usage:
        from eden.exceptions import error_handler_registry
        
        # Register custom handler
        error_handler_registry.register(CustomErrorHandler())
        
        # Get handlers for dispatch
        handler = error_handler_registry.get_handler(exc)
    """

    def __init__(self):
        """Initialize with default handlers."""
        self._handlers: list[ErrorHandler] = [
            StarletteHTTPErrorHandler(),
            DefaultErrorHandler()
        ]

    def register(self, handler: ErrorHandler, priority: int = 100) -> None:
        """
        Register an error handler.
        
        Args:
            handler: ErrorHandler instance
            priority: Insertion priority (higher = checked first)
                     Default 100 means checks after default (1)
        
        Implementation Notes:
            - Handlers are checked in registration order
            - First matching handler handles the exception
            - DefaultErrorHandler is always last fallback
        """
        self._handlers.insert(0, handler)  # Add to front (checked first)
        logger.info(f"Registered error handler: {handler.__class__.__name__}")

    def clear_custom_handlers(self) -> None:
        """
        Clear all custom handlers, keeping only default.
        
        Useful for testing or resetting error handling.
        """
        self._handlers = [DefaultErrorHandler()]

    async def handle_exception(self, exc: Exception, request, app):
        """
        Find and invoke appropriate handler for exception.
        
        Args:
            exc: Exception to handle
            request: Starlette Request
            app: Eden application
        
        Returns:
            Starlette Response from matched handler
        """
        for handler in self._handlers:
            if handler.matches(exc):
                try:
                    response = await handler.handle(exc, request, app)
                    logger.debug(f"Handled {type(exc).__name__} with {handler.__class__.__name__}")
                    return response
                except Exception as handler_error:
                    logger.error(f"Error handler failed: {handler_error}")
                    # Try next handler
                    continue
        
        # Should never reach here (DefaultErrorHandler matches all)
        logger.error(f"No handler found for {type(exc).__name__}")
        from eden.responses import JsonResponse
        return JsonResponse({"error": True, "detail": "Internal server error."}, status_code=500)


# Global error handler registry instance
error_handler_registry = ErrorHandlerRegistry()
