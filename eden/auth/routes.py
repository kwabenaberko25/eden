"""
Eden — Built-in Authentication Routes

Provides secure, CSRF-protected login/logout routes.
These are optional — users can mount them or build their own.
"""

import logging
from eden.routing import Router
from eden.requests import Request
from eden.responses import JSONResponse, RedirectResponse
from eden.auth.decorators import login_required
from eden.middleware.rate_limit import rate_limit

logger = logging.getLogger(__name__)

auth_router = Router(prefix="/auth")


@auth_router.post("/logout")
@login_required
async def logout_view(request: Request):
    """
    Secure logout endpoint.
    
    - Requires POST (GET is rejected by route definition).
    - CSRF protection is enforced by CSRFMiddleware (which applies to POST).
    - Revokes JWT tokens if present.
    
    Returns:
        JSON response confirming logout, or redirect to login page.
    """
    from eden.auth.actions import logout
    await logout(request, revoke_tokens=True)
    
    # Check if client expects JSON (API) or HTML (browser)
    accept = request.headers.get("accept", "")
    if "application/json" in accept:
        return JSONResponse({"detail": "Logged out successfully."})
    
    # Browser redirect
    return RedirectResponse(url="/login", status_code=303)


@auth_router.post("/login")
@rate_limit("5/minute")
async def login_view(request: Request):
    """
    Secure login endpoint with rate limiting.
    
    Rate limited to 5 attempts per minute per IP to prevent brute-force attacks.
    Always returns a generic error message to prevent user enumeration.
    
    Expects JSON body: {"email": "...", "password": "..."}
    """
    from eden.auth.actions import authenticate, login
    from eden.auth.audit import auth_audit
    
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            {"error": True, "detail": "Invalid request body."},
            status_code=400,
        )
    
    email = body.get("email", "")
    password = body.get("password", "")
    
    if not email or not password:
        return JSONResponse(
            {"error": True, "detail": "Email and password are required."},
            status_code=400,
        )
    
    # Get the auth manager from the request context
    user = None
    if hasattr(request, "ctx"):
        user = await request.ctx.auth.authenticate(email, password)
    else:
        # Fallback to module-level function
        user = await authenticate(email, password)
    
    if not user:
        # Generic message — do NOT reveal whether email exists
        auth_audit.login_failed(request, email=email, reason="invalid_credentials")
        return JSONResponse(
            {"error": True, "detail": "Invalid credentials."},
            status_code=401,
        )
    
    await login(request, user)
    
    accept = request.headers.get("accept", "")
    if "application/json" in accept:
        return JSONResponse({"detail": "Login successful.", "user_id": str(user.id)})
    
    return RedirectResponse(url="/", status_code=303)
