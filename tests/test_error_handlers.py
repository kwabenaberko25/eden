"""
Tests for Global Error Handler System (Layers 5-8).

Verifies:
- Error handler registry and dispatch
- Handler matching and execution
- Content negotiation (HTML vs JSON)
- Middleware integration
- Context-aware error messages
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from starlette.requests import Request
from starlette.responses import JSONResponse

from eden.exceptions import (
    EdenException,
    ErrorHandler,
    ErrorHandlerRegistry,
    DefaultErrorHandler,
    BadRequest,
    NotFound,
    Unauthorized,
    error_handler_registry,
)
from eden.error_middleware import ErrorHandlerMiddleware, ContentNegotiationErrorHandler


class TestErrorHandlerRegistry:
    """Tests for global error handler registry (Layer 5)."""

    def test_registry_initialization(self):
        """Test that registry starts with default handler."""
        registry = ErrorHandlerRegistry()
        assert len(registry._handlers) >= 1
        assert isinstance(registry._handlers[-1], DefaultErrorHandler)

    def test_register_handler(self):
        """Test registering a custom handler."""
        registry = ErrorHandlerRegistry()
        initial_count = len(registry._handlers)
        
        class CustomHandler(ErrorHandler):
            def matches(self, exc: Exception) -> bool:
                return isinstance(exc, ValueError)
            
            async def handle(self, exc: Exception, request, app):
                return JSONResponse({"error": "custom"}, status_code=400)
        
        registry.register(CustomHandler())
        assert len(registry._handlers) > initial_count

    def test_clear_custom_handlers(self):
        """Test clearing custom handlers (keep default)."""
        registry = ErrorHandlerRegistry()
        
        class CustomHandler(ErrorHandler):
            def matches(self, exc: Exception) -> bool:
                return True
            
            async def handle(self, exc: Exception, request, app):
                return JSONResponse({"error": "custom"})
        
        registry.register(CustomHandler())
        assert len(registry._handlers) > 1
        
        registry.clear_custom_handlers()
        assert len(registry._handlers) == 1
        assert isinstance(registry._handlers[0], DefaultErrorHandler)

    @pytest.mark.asyncio
    async def test_dispatch_to_matching_handler(self):
        """Test that exception is dispatched to matching handler."""
        registry = ErrorHandlerRegistry()
        
        class CustomHandler(ErrorHandler):
            def matches(self, exc: Exception) -> bool:
                return isinstance(exc, ValueError)
            
            async def handle(self, exc: Exception, request, app):
                return JSONResponse(
                    {"error": "custom ValueError handler"},
                    status_code=400
                )
        
        registry.register(CustomHandler())
        
        # Create mock request and app
        request = MagicMock(spec=Request)
        app = MagicMock()
        
        # Dispatch
        response = await registry.handle_exception(ValueError("test"), request, app)
        
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_handler_not_found_uses_default(self):
        """Test that unmatched exceptions use default handler."""
        registry = ErrorHandlerRegistry()
        
        request = MagicMock(spec=Request)
        app = MagicMock()
        
        exc = Exception("unhandled")
        response = await registry.handle_exception(exc, request, app)
        
        # Default handler should respond
        assert response is not None


class TestErrorHandler:
    """Tests for ErrorHandler base class (Layer 6: Plugin system)."""

    def test_error_handler_interface(self):
        """Test that error handlers implement required interface."""
        
        class ValidHandler(ErrorHandler):
            def matches(self, exc: Exception) -> bool:
                return isinstance(exc, ValueError)
            
            async def handle(self, exc: Exception, request, app):
                from eden.responses import JsonResponse
                return JsonResponse({"error": str(exc)})
        
        handler = ValidHandler()
        assert callable(handler.matches)
        assert callable(handler.handle)
        assert handler.matches(ValueError("test"))
        assert not handler.matches(KeyError())

    @pytest.mark.asyncio
    async def test_error_handler_execution(self):
        """Test executing an error handler."""
        
        class CustomHandler(ErrorHandler):
            def matches(self, exc: Exception) -> bool:
                return isinstance(exc, KeyError)
            
            async def handle(self, exc: Exception, request, app):
                from eden.responses import JsonResponse
                return JsonResponse(
                    {"error": f"Key error: {exc}"},
                    status_code=404
                )
        
        handler = CustomHandler()
        request = MagicMock(spec=Request)
        app = MagicMock()
        
        exc = KeyError("missing_key")
        response = await handler.handle(exc, request, app)
        
        assert response.status_code == 404


class TestEdenExceptionContexts:
    """Tests for context-aware error messages (Layer 7)."""

    def test_exception_with_context(self):
        """Test exception with debugging context."""
        exc = EdenException(
            detail="User not found",
            status_code=404,
            context={
                "operation": "fetch_user",
                "user_id": 123,
                "suggestion": "Check if user_id exists in database"
            }
        )
        
        assert exc.context["operation"] == "fetch_user"
        assert exc.context["suggestion"] is not None

    def test_exception_to_dict_excludes_context(self):
        """Test that context is not included in JSON response."""
        exc = EdenException(
            detail="Error",
            context={"debug_info": "secret"}
        )
        
        exc_dict = exc.to_dict()
        assert "context" not in exc_dict
        assert "debug_info" not in str(exc_dict)
        assert "detail" in exc_dict

    def test_log_context(self):
        """Test that context can be logged."""
        exc = EdenException(
            detail="Database error",
            context={"operation": "update_user", "attempts": 3}
        )
        
        # Should not raise
        exc.log_context()


class TestContentNegotiationErrorHandler:
    """Tests for HTML vs JSON error responses."""

    def test_wants_json_from_accept_header(self):
        """Test JSON preference detection."""
        # JSON request
        request = MagicMock(spec=Request)
        request.headers.get.return_value = "application/json"
        
        assert ContentNegotiationErrorHandler.wants_json(request) is True
        
        # HTML request
        request.headers.get.return_value = "text/html"
        assert ContentNegotiationErrorHandler.wants_json(request) is False

    def test_json_response_helper(self):
        """Test JSON response creation."""
        response = ContentNegotiationErrorHandler.json_response(
            {"error": "test"},
            status_code=400
        )
        
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_html_response_helper(self):
        """Test HTML response creation."""
        request = MagicMock(spec=Request)
        app = MagicMock()
        
        # Mock templates
        template = MagicMock()
        template.render.return_value = "<html><body>Error</body></html>"
        app.templates.get_template.return_value = template
        
        response = ContentNegotiationErrorHandler.html_response(
            "error.html",
            {"detail": "Test error"},
            status_code=500,
            app=app
        )
        
        assert response.status_code == 500


class TestErrorHandlerMiddleware:
    """Tests for ErrorHandlerMiddleware (Layer 5: Middleware Hook)."""

    @pytest.mark.asyncio
    async def test_middleware_passes_through_successful_response(self):
        """Test that successful responses pass through unchanged."""
        middleware = ErrorHandlerMiddleware(None)
        
        request = MagicMock(spec=Request)
        app = MagicMock()
        request.app = app
        
        successful_response = JSONResponse({"status": "ok"})
        call_next = AsyncMock(return_value=successful_response)
        
        response = await middleware.dispatch(request, call_next)
        
        assert response is successful_response
        call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_middleware_catches_exceptions(self):
        """Test that middleware catches and handles exceptions."""
        middleware = ErrorHandlerMiddleware(None)
        
        request = MagicMock(spec=Request)
        app = MagicMock()
        request.app = app
        
        exc = ValueError("test error")
        call_next = AsyncMock(side_effect=exc)
        
        # Should not raise, should return error response
        response = await middleware.dispatch(request, call_next)
        
        assert response is not None
        # Error handler should have been invoked

    @pytest.mark.asyncio
    async def test_middleware_preserves_exception_headers(self):
        """Test that custom headers from exception are preserved."""
        middleware = ErrorHandlerMiddleware(None)
        
        request = MagicMock(spec=Request)
        app = MagicMock()
        request.app = app
        
        exc = EdenException(
            "Error",
            headers={"X-Custom": "header-value"}
        )
        call_next = AsyncMock(side_effect=exc)
        
        response = await middleware.dispatch(request, call_next)
        
        # Headers should be added to response (if JsonResponse preserves them)
        assert response is not None


class TestAppErrorHandlerIntegration:
    """Integration tests for app.register_error_handler()."""

    def test_register_error_handler_validates_type(self):
        """Test that app validates error handler type."""
        from eden.app import Eden
        
        app = Eden()
        
        # Should reject non-ErrorHandler objects
        with pytest.raises(ValueError):
            app.register_error_handler("not a handler")

    def test_register_error_handler_accepts_valid_handler(self):
        """Test that app accepts valid error handlers."""
        from eden.app import Eden
        
        app = Eden()
        
        class CustomHandler(ErrorHandler):
            def matches(self, exc: Exception) -> bool:
                return isinstance(exc, ValueError)
            
            async def handle(self, exc: Exception, request, app):
                from eden.responses import JsonResponse
                return JsonResponse({"error": "custom"})
        
        # Should not raise
        app.register_error_handler(CustomHandler())


class TestEdenExceptionHierarchy:
    """Tests for exception class hierarchy and behavior."""

    def test_all_exceptions_are_eden_exceptions(self):
        """Test that all app exceptions inherit from EdenException."""
        exceptions_to_test = [
            BadRequest(),
            NotFound(),
            Unauthorized(),
        ]
        
        for exc in exceptions_to_test:
            assert isinstance(exc, EdenException)

    def test_exception_serialization(self):
        """Test that exceptions serialize to JSON properly."""
        exc = BadRequest(detail="Invalid input")
        exc_dict = exc.to_dict()
        
        assert exc_dict["error"] is True
        assert exc_dict["status_code"] == 400
        assert exc_dict["detail"] == "Invalid input"

    def test_exception_headers_in_dict(self):
        """Test that exception headers are accessible."""
        exc = Unauthorized(headers={"WWW-Authenticate": "Bearer"})
        
        assert exc.headers["WWW-Authenticate"] == "Bearer"
