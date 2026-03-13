"""
Eden — CSRF Protection
"""

import secrets
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

CSRF_SECRET_KEY = "eden_csrf_token"

def generate_csrf_token() -> str:
    """
    Generate a new random CSRF token.
    """
    return secrets.token_urlsafe(32)

class CSRFMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces CSRF protection.
    """
    def __init__(self, app: ASGIApp, exclude_paths: list | None = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or []

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get token from session
        csrf_token = request.session.get(CSRF_SECRET_KEY)

        # If no token in session, generate one and set it
        if not csrf_token:
            csrf_token = generate_csrf_token()
            request.session[CSRF_SECRET_KEY] = csrf_token

        # Check for mutation methods
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            # Check for exclusions
            if any(request.url.path.startswith(path) for path in self.exclude_paths):
                return await call_next(request)

            # Check for token in request (Header first, then Form)
            request_token = request.headers.get("X-CSRF-Token")

            if not request_token:
                # Try to get from form data if it's a form request
                try:
                    form_data = await request.form()
                    request_token = form_data.get("csrf_token")
                except (ValueError, RuntimeError):
                    # ValueError: request body already consumed
                    # RuntimeError: form parsing failed
                    pass

            if not request_token or request_token != csrf_token:
                return JSONResponse(
                    {"error": "CSRF token missing or invalid"},
                    status_code=403
                )

        response = await call_next(request)
        
        # Set the CSRF token in a cookie for HTMX/JS access
        # Only set if the token is in the session
        if csrf_token:
            response.set_cookie(
                "csrftoken",
                csrf_token,
                httponly=False,  # Allow JS to read it for HTMX headers
                samesite="lax",
                secure=request.url.scheme == "https"
            )
        
        return response

def get_csrf_token(request: Request) -> str:
    """
    Get the current CSRF token from the session.
    Falls back to generating a token if session is not available.
    """
    # Handle case where SessionMiddleware is not configured
    if not hasattr(request, "session") or request.session is None:
        # Return a newly generated token (won't be validated, but allows page rendering)
        return generate_csrf_token()
    
    token = request.session.get(CSRF_SECRET_KEY)
    if not token:
        token = generate_csrf_token()
        request.session[CSRF_SECRET_KEY] = token
    return token
