"""
Eden — Authentication Middleware

Handles user authentication and centralized authorization.
"""

import logging
from collections.abc import Sequence
from typing import Any, Optional

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse

from eden.auth.base import AuthBackend
from eden.context import reset_request, reset_user, set_request, set_user
from eden.requests import Request
from eden.exceptions import Unauthorized, Forbidden

logger = logging.getLogger(__name__)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Middleware that tries to authenticate the request using one or more backends.
    """

    def __init__(self, app: Any, backends: Optional[Sequence[AuthBackend]] = None, **kwargs) -> None:
        super().__init__(app, **kwargs)
        if backends is None:
            from eden.auth.backends.session import SessionBackend
            backends = [SessionBackend()]
        self.backends = backends

    async def dispatch(
        self, request: StarletteRequest, call_next: RequestResponseEndpoint
    ) -> StarletteResponse:
        # Wrap Starlette request in Eden wrapper if not already
        eden_request = Request.from_scope(request.scope, request.receive, request._send)
        
        # 1. Set request in context
        req_token = set_request(eden_request)
        user_token = None

        try:
            user = None
            for backend in self.backends:
                try:
                    user = await backend.authenticate(eden_request)
                except Exception as e:
                    logger.debug(f"Backend {backend.__class__.__name__} auth failed: {e}")
                    pass

                if user:
                    break

            # 2. Set user in context and request state
            if user:
                user_token = set_user(user)
                request.state.user = user
                eden_request.user = user
            else:
                request.state.user = None
                eden_request.user = None

            response = await call_next(request)
            return response

        finally:
            # 3. Cleanup context
            if user_token:
                reset_user(user_token)
            reset_request(req_token)


class AuthorizationMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces RBAC and permissions based on route metadata.
    Complements decorators by providing a centralized enforcement point.
    """

    async def dispatch(
        self, request: StarletteRequest, call_next: RequestResponseEndpoint
    ) -> StarletteResponse:
        # 1. Get endpoint from scope
        endpoint = request.scope.get("endpoint")
        if not endpoint:
            return await call_next(request)

        # 2. Extract user
        user = getattr(request.state, "user", None)
        
        # 3. Deny if login is required but user is missing
        if getattr(endpoint, "_login_required", False) and not user:
             raise Unauthorized(detail="Login required.")

        # 4. Check single permission requirement
        required_permission = getattr(endpoint, "_required_permission", None)
        if required_permission:
            if not user:
                raise Unauthorized(detail="Login required.")
            
            from eden.auth.access import check_permission
            if not await check_permission(user, f"can_{required_permission}", None):
                # Note: f"can_{required_permission}" is to match typical Eden naming
                if not await check_permission(user, required_permission, None):
                    raise Forbidden(detail=f"Missing required permission: {required_permission}")

        # 5. Check required roles
        required_roles = getattr(endpoint, "_required_roles", None)
        if required_roles:
            if not user:
                raise Unauthorized(detail="Login required.")
            
            user_roles = []
            if hasattr(user, "get_roles"):
                user_roles = user.get_roles()
            elif hasattr(user, "roles"):
                user_roles = user.roles

            if not any(role in user_roles for role in required_roles):
                if not getattr(user, "is_superuser", False):
                    raise Forbidden(detail=f"Missing one of the required roles: {', '.join(required_roles)}")

        return await call_next(request)
