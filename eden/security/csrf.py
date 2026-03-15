"""
Eden — CSRF Protection (Backward Compatibility Wrapper)

⚠️  DEPRECATED: Import from eden.middleware instead
────────────────────────────────────────────────────

This module is now a backward-compatibility wrapper around eden.middleware.CSRFMiddleware.
All CSRF protection is implemented in eden/middleware.py for performance reasons.

MIGRATION GUIDE:
────────────────
Old (deprecated but still works):
    from eden.security.csrf import CSRFMiddleware, get_csrf_token

New (recommended):
    from eden.middleware import CSRFMiddleware, get_csrf_token

ACTION REQUIRED:
    If you have custom code importing from this module:
    1. Change imports to use eden.middleware
    2. Test your application
    3. Update your code to use the new location

For questions, see: eden/middleware.py CSRFMiddleware docstring
                    and MIDDLEWARE_EXECUTION_ORDER documentation
"""

import secrets
from typing import TYPE_CHECKING

# Import the primary implementations from eden.middleware
from eden.middleware import (
    CSRFMiddleware as _CSRFMiddlewareImpl,
    get_csrf_token as _get_csrf_token,
)

if TYPE_CHECKING:
    from starlette.requests import Request

# Re-export for backward compatibility
CSRFMiddleware = _CSRFMiddlewareImpl
get_csrf_token = _get_csrf_token

# Legacy constant for backward compatibility
CSRF_SECRET_KEY = "eden_csrf_token"


def generate_csrf_token() -> str:
    """
    Generate a new random CSRF token.
    
    ⚠️  DEPRECATED: This is a legacy helper for backward compatibility.
    The primary implementations in eden.middleware handle generation
    automatically. Use get_csrf_token(request) instead.
    """
    return secrets.token_urlsafe(32)


__all__ = [
    "CSRFMiddleware",
    "get_csrf_token",
    "CSRF_SECRET_KEY",
    "generate_csrf_token",
]
