
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

        from eden.exceptions.debug import render_error_response
        return StarletteResponse(
            content=render_error_response(
                status_code=exc.status_code,
                detail=exc.detail,
                traceback_text=None
            ),
            status_code=exc.status_code,
            media_type="text/html"
        )

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

        # Special handling for Template errors in debug mode
        if self.app.debug and isinstance(exc, JinjaTemplateError):
            # This would still need some of the extraction logic from app.py
            # For now, we'll keep the specialized logic in app.py but call it here
            # Or better, move the extraction logic to a helper.
            return self.app._render_enhanced_template_error(request, exc)

        status_code = getattr(exc, "status_code", 500)
        detail = getattr(exc, "detail", str(exc)) if self.app.debug else "Internal server error."
        if not self.app.debug and status_code == 404:
            detail = "Page not found."
        elif not self.app.debug and status_code == 405:
            detail = "Method not allowed."

        traceback_text = None
        if self.app.debug:
            import traceback
            traceback_text = traceback.format_exc()
            
        return StarletteResponse(
            content=render_error_response(
                status_code=status_code,
                detail=detail,
                traceback_text=traceback_text
            ),
            status_code=status_code,
            media_type="text/html"
        )
