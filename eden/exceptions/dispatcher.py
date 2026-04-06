
from __future__ import annotations
import inspect
from typing import Any, Callable, TYPE_CHECKING
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse

if TYPE_CHECKING:
    from eden.app import Eden
    from eden.requests import Request
    from eden.exceptions import EdenException

class ExceptionDispatcher:
    """Dispatches exceptions to registered handlers or default Eden handlers."""
    
    def __init__(self, app: Eden):
        self.app = app

    async def handle_eden_exception(
        self, request: Request, exc: EdenException
    ) -> StarletteResponse:
        """Handle Eden-specific exceptions."""
        handler = self.app._exception_handlers.get(type(exc))
        if handler:
            result = handler(request, exc)
            if inspect.isawaitable(result):
                result = await result
            return result

        # Use the exception's own serialization if possible
        extra = getattr(exc, "extra", None)
        return await self._error_response(request, exc.status_code, exc.detail, extra=extra)

    async def handle_unhandled_exception(
        self, request: Request, exc: Exception
    ) -> StarletteResponse:
        """Handle unexpected exceptions."""
        from jinja2.exceptions import TemplateError as JinjaTemplateError
        from eden.exceptions.debug import render_error_response, render_premium_debug_page

        # Check for a generic Exception handler
        handler = self.app._exception_handlers.get(Exception)
        if handler:
            result = handler(request, exc)
            if inspect.isawaitable(result):
                result = await result
            return result

        # Special handling for Eden exceptions
        from eden.exceptions import EdenException
        if isinstance(exc, EdenException):
            return await self.handle_eden_exception(request, exc)

        # Special handling for Template errors in debug mode
        if self.app.debug and isinstance(exc, JinjaTemplateError):
            return self.app._render_enhanced_template_error(request, exc)

        status_code = getattr(exc, "status_code", 500)
        detail = getattr(exc, "detail", None)
        
        if detail is None:
            if self.app.debug:
                detail = str(exc)
            else:
                if status_code == 404:
                    detail = "Page not found."
                elif status_code == 405:
                    detail = "Method not allowed."
                else:
                    detail = "Internal server error."
        
        traceback_text = None
        if self.app.debug:
            import traceback
            traceback_text = traceback.format_exc()
            
        return await self._error_response(request, status_code, detail, traceback_text)

    async def _error_response(
        self, 
        request: Request, 
        status_code: int, 
        detail: str, 
        traceback_text: str | None = None,
        extra: dict | None = None
    ) -> StarletteResponse:
        """Helper to create a JSON or HTML response based on Accept header."""
        accept = request.headers.get("accept", "").lower()
        
        # 1. Prefer JSON if explicitly requested, AJAX, or if in test mode
        # In tests, we almost always want JSON unless they explicitly asked for HTML
        is_test = self.app.is_test()
        should_use_json = (
            "application/json" in accept or 
            request.headers.get("x-requested-with") == "XMLHttpRequest" or
            (is_test and "text/html" not in accept)
        )
        
        if should_use_json:
            from starlette.responses import JSONResponse
            content = {"error": True, "status_code": status_code, "detail": detail}
            if extra:
                content["extra"] = extra
            if self.app.debug and traceback_text:
                content["traceback"] = traceback_text
            return JSONResponse(content, status_code=status_code)

        # 2. Default to Eden's Premium HTML error page
        from eden.exceptions.debug import render_error_response
        return StarletteResponse(
            content=render_error_response(
                status_code=status_code,
                detail=detail,
                traceback_text=traceback_text
            ),
            status_code=status_code,
            media_type="text/html"
        )
