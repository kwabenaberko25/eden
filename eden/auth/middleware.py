"""
Eden — Authentication Middleware

Handles user authentication and centralized authorization.
"""

import logging
from collections.abc import Sequence
from typing import Any, Optional

from starlette.types import ASGIApp, Receive, Scope, Send, Message

from eden.auth.base import AuthBackend
from eden.context import reset_request, reset_user, set_request, set_user
from eden.requests import Request
from eden.exceptions import Unauthorized, Forbidden

logger = logging.getLogger(__name__)


class AuthenticationMiddleware:
    """
    Middleware that tries to authenticate the request using one or more backends.
    
    Refactored to pure ASGI for performance and clean context management.
    """

    def __init__(self, app: ASGIApp, backends: Optional[Sequence[AuthBackend]] = None, **kwargs) -> None:
        self.app = app
        if backends is None:
            # Lazy import backends to avoid circular dependencies
            from eden.auth.backends.session import SessionBackend
            backends = [SessionBackend()]
        self.backends = backends

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        """Compatibility wrapper for tests calling .dispatch directly."""
        # 1. Set request in context
        req_token = set_request(request)
        user_token = None

        try:
            user = None
            for backend in self.backends:
                try:
                    user = await backend.authenticate(request)
                except Exception as e:
                    logger.debug(f"Backend {backend.__class__.__name__} auth failed: {e}")
                    pass

                if user:
                    break

            # 2. Set user in context and request state
            if user:
                # Check absolute session expiry
                if hasattr(request, "session"):
                    import datetime
                    auth_at_str = request.session.get("_auth_authenticated_at")
                    if auth_at_str:
                        try:
                            auth_at = datetime.datetime.fromisoformat(auth_at_str)
                            now = datetime.datetime.now(datetime.UTC)
                            # Get max age from app config, default 30 days
                            max_age = 30 * 24 * 60 * 60
                            try:
                                from eden.config import get_config
                                max_age = get_config().session_absolute_max_age
                            except Exception:
                                pass
                            
                            if (now - auth_at).total_seconds() > max_age:
                                logger.info("Session expired (absolute expiry). Forcing re-login.")
                                user = None
                                # Clear the expired session
                                request.session.pop("_auth_user_id", None)
                                request.session.pop("_auth_authenticated_at", None)
                        except (ValueError, TypeError):
                            pass
                
                if user:
                    user_token = set_user(user)
                    # Ensure user is available in both scope and request
                    request.scope["user"] = user
                    request.user = user
                    # Stay compatible with Starlette state if used
                    if "state" not in request.scope:
                        request.scope["state"] = {}
                    request.scope["state"]["user"] = user
                else:
                    request.scope["user"] = None
                    request.user = None
                    if "state" in request.scope:
                        request.scope["state"]["user"] = None
            else:
                request.scope["user"] = None
                request.user = None
                if "state" in request.scope:
                    request.scope["state"]["user"] = None

            # 3. Proceed down the middleware chain
            return await call_next(request)

        finally:
            # 4. Cleanup context
            if user_token:
                reset_user(user_token)
            reset_request(req_token)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI middleware entry point."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Wrap scope/receive/send in Eden Request
        request = Request(scope, receive, send)
        
        # 1. Set request in context
        req_token = set_request(request)
        user_token = None

        try:
            user = None
            for backend in self.backends:
                try:
                    user = await backend.authenticate(request)
                except Exception as e:
                    logger.debug(f"Backend {backend.__class__.__name__} auth failed: {e}")
                    pass

                if user:
                    break

            # 2. Set user in context and request state
            if user:
                # Check absolute session expiry
                if hasattr(request, "session"):
                    import datetime
                    auth_at_str = request.session.get("_auth_authenticated_at")
                    if auth_at_str:
                        try:
                            auth_at = datetime.datetime.fromisoformat(auth_at_str)
                            now = datetime.datetime.now(datetime.UTC)
                            # Get max age from app config, default 30 days
                            max_age = 30 * 24 * 60 * 60
                            try:
                                from eden.config import get_config
                                max_age = get_config().session_absolute_max_age
                            except Exception:
                                pass
                            
                            if (now - auth_at).total_seconds() > max_age:
                                logger.info("Session expired (absolute expiry). Forcing re-login.")
                                user = None
                                # Clear the expired session
                                request.session.pop("_auth_user_id", None)
                                request.session.pop("_auth_authenticated_at", None)
                        except (ValueError, TypeError):
                            pass
                
                if user:
                    user_token = set_user(user)
                    # Ensure user is available in both scope and request
                    scope["user"] = user
                    request.user = user
                    # Stay compatible with Starlette state if used
                    if "state" not in scope:
                        scope["state"] = {}
                    scope["state"]["user"] = user
                else:
                    scope["user"] = None
                    request.user = None
                    if "state" in scope:
                        scope["state"]["user"] = None
            else:
                scope["user"] = None
                request.user = None
                if "state" in scope:
                    scope["state"]["user"] = None

            # 3. Proceed down the middleware chain
            await self.app(scope, receive, send)

        finally:
            # 4. Cleanup context
            if user_token:
                reset_user(user_token)
            reset_request(req_token)


class AuthorizationMiddleware:
    """
    Middleware that enforces RBAC and permissions based on route metadata.
    Complements decorators by providing a centralized enforcement point.
    
    Refactored to pure ASGI for performance.
    """

    def __init__(self, app: ASGIApp, **kwargs) -> None:
        self.app = app

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        """Compatibility wrapper for tests calling .dispatch directly."""
        # 1. Get endpoint from scope (already resolved by Router)
        scope = request.scope
        endpoint = scope.get("endpoint")
        if not endpoint:
            return await call_next(request)

        # 2. Extract user
        user = scope.get("user") or (scope.get("state", {}).get("user"))
        
        # 3. Deny if login is required but user is missing
        if getattr(endpoint, "_login_required", False) and not user:
             raise Unauthorized(detail="Login required.")

        # 4. Check single permission requirement
        required_permission = getattr(endpoint, "_required_permission", None)
        if required_permission:
            if not user:
                raise Unauthorized(detail="Login required.")
            
            from eden.auth.access import check_permission
            # Try with 'can_' prefix (typical Eden pattern) and without
            if not await check_permission(user, f"can_{required_permission}", None):
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

        # 6. Proceed if all checks pass
        return await call_next(request)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI middleware entry point."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # 1. Get endpoint from scope (already resolved by Router)
        endpoint = scope.get("endpoint")
        if not endpoint:
            await self.app(scope, receive, send)
            return

        # 2. Extract user
        user = scope.get("user") or (scope.get("state", {}).get("user"))
        
        # 3. Deny if login is required but user is missing
        if getattr(endpoint, "_login_required", False) and not user:
             raise Unauthorized(detail="Login required.")

        # 4. Check single permission requirement
        required_permission = getattr(endpoint, "_required_permission", None)
        if required_permission:
            if not user:
                raise Unauthorized(detail="Login required.")
            
            from eden.auth.access import check_permission
            # Try with 'can_' prefix (typical Eden pattern) and without
            if not await check_permission(user, f"can_{required_permission}", None):
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

        # 6. Proceed if all checks pass
        await self.app(scope, receive, send)
