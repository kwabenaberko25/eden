"""
Eden — Authentication Middleware
"""

from collections.abc import Sequence
from typing import Any, Optional

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse

from eden.auth.base import AuthBackend
from eden.context import reset_request, reset_user, set_request, set_user
from eden.requests import Request


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
        # Get or create Eden request for backends
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
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.debug(f"Backend {backend.__class__.__name__} auth failed: {e}")
                    pass

                if user:
                    break

            # 2. Set user in context and request state
            if user:
                user_token = set_user(user)
                request.state.user = user
                eden_request.user = user  # Ensure it's on the wrapper too
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
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> StarletteResponse:
        # 1. Get endpoint from scope
        endpoint = request.scope.get("endpoint")
        if not endpoint:
            return await call_next(request)

        # 2. Extract user
        user = getattr(request.state, "user", None)
        
        # 3. Check for auth/perm requirements on the endpoint
        # The endpoint might be a wrapped version, so we check both
        
        # Check login requirement
        if getattr(endpoint, "_login_required", False) and not user:
             from eden.exceptions import Unauthorized
             raise Unauthorized(detail="Login required.")

        # Check single permission
        required_permission = getattr(endpoint, "_required_permission", None)
        if required_permission:
            if not user:
                from eden.exceptions import Unauthorized
                raise Unauthorized(detail="Login required.")
            
            from eden.auth.query_filtering import user_has_permission
            if not user_has_permission(user, required_permission):
                from eden.exceptions import Forbidden
                raise Forbidden(detail=f"Missing required permission: {required_permission}")

        # Check required roles
        required_roles = getattr(endpoint, "_required_roles", None)
        if required_roles:
            if not user:
                from eden.exceptions import Unauthorized
                raise Unauthorized(detail="Login required.")
            
            from eden.auth.query_filtering import user_has_any_role
            if not user_has_any_role(user, *required_roles):
                from eden.exceptions import Forbidden
                raise Forbidden(detail=f"Missing one of the required roles: {', '.join(required_roles)}")

        return await call_next(request)
