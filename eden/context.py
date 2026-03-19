"""
Eden — Async Context Propagation System (Layer 1)

Centralized context management for request-scoped data using ContextVars.

Provides:
- Lifecycle hooks (on_request_start, on_request_end)
- Safe context get/set with fallback values
- Automatic cleanup on request end
- Thread-safe and async-safe context isolation
- Request ID correlation for logging

Usage:
    from eden.context import context_manager, get_user, get_app, get_request_id
    
    # In middleware:
    await context_manager.on_request_start(request, app)
    user = get_user()  # None if not authenticated
    request_id = get_request_id()  # Auto-generated UUID
    
    # Cleanup via ContextMiddleware
    await context_manager.on_request_end()

Design Philosophy:
- All context vars defined in one place (centralized ownership)
- Consistent set/get patterns with sensible defaults
- Automatic cleanup prevents context leaks
- Request ID enables distributed logging (correlation)
- Extensible with run_in_context() for background tasks
"""

from __future__ import annotations

import contextvars
import logging
import uuid
from typing import TYPE_CHECKING, Any, Optional, Callable, Awaitable

if TYPE_CHECKING:
    from eden.requests import Request

logger = logging.getLogger(__name__)

# Context variables (one per data type, defined centrally)
_request_ctx = contextvars.ContextVar("eden_request", default=None)
_user_ctx = contextvars.ContextVar("eden_user", default=None)
_app_ctx = contextvars.ContextVar("eden_app", default=None)
_request_id_ctx = contextvars.ContextVar("eden_request_id", default="")
_tenant_id_ctx = contextvars.ContextVar("eden_tenant_id", default=None)


class ContextManager:
    """
    Centralized async context lifecycle manager.

    Manages initialization, cleanup, and safe access to all context-scoped data.
    Designed to be used by ASGI middleware (ContextMiddleware).

    Lifecycle:
        1. on_request_start() → Initialize context at request beginning
        2. Code runs, accessing context via get_* functions
        3. on_request_end() → Cleanup context at request end

    Example:
        >>> manager = ContextManager()
        >>> # In middleware on_request_start:
        >>> await manager.on_request_start(request, app)
        >>> request_id = manager.get_request_id()  # Auto-generated UUID
        >>> # In middleware on_request_end:
        >>> await manager.on_request_end()
    """

    async def on_request_start(
        self, request: "Request", app: Any
    ) -> None:
        """
        Initialize context at request start.

        Sets up all request-scoped context vars. Should be called from middleware
        before routing/handling the request.

        Args:
            request: Starlette Request object (contains method, path, headers, etc.)
            app: Eden application instance

        Implementation Notes:
            - Generates unique request_id for this request (for logging correlation)
            - Sets app and request in context
            - User/tenant remain unset until explicitly set by auth/tenancy middleware
            - Safe to call multiple times (idempotent per context copy)
        """
        # Generate unique request ID for correlation across logs
        request_id = str(uuid.uuid4())

        # Set context vars in this context (ContextVars are thread/task-local)
        _request_id_ctx.set(request_id)
        _app_ctx.set(app)
        _request_ctx.set(request)
        # User and tenant remain None until explicitly set

        logger.debug(
            f"Context initialized: request_id={request_id}, path={request.url.path}"
        )

    async def on_request_end(self) -> None:
        """
        Cleanup context at request end.

        Resets all context vars to their default values. Prevents context leaks
        when using thread pools or task reuse. Should be called from middleware
        in a finally block.

        Implementation Notes:
            - Safe to call even if context wasn't initialized
            - Idempotent (multiple calls have same effect)
            - Does NOT raise exceptions; logs warnings instead
        """
        try:
            # Log any user/tenant context for audit trail
            user = _user_ctx.get(None)
            tenant_id = _tenant_id_ctx.get(None)
            request_id = _request_id_ctx.get("")

            if user is not None or tenant_id is not None:
                logger.debug(
                    f"Request context ending: request_id={request_id}, "
                    f"user={getattr(user, 'id', user)}, tenant_id={tenant_id}"
                )

            # Reset all context vars to defaults
            _app_ctx.set(None)
            _request_ctx.set(None)
            _user_ctx.set(None)
            _tenant_id_ctx.set(None)
            _request_id_ctx.set("")

            # Sync cleanup with internal tenancy context for ORM isolation
            try:
                from eden.tenancy.context import _tenant_ctx
                _tenant_ctx.set(None)
            except ImportError:
                # If tenancy is not available, nothing to cleanup
                pass

        except Exception as e:
            logger.warning(f"Error cleaning up context: {e}")

    def set_user(self, user: Any) -> contextvars.Token:
        """
        Set current user in context (called by auth middleware).

        Args:
            user: User object (e.g., BaseUser instance, None to clear)

        Example:
            >>> from eden.auth import get_current_user
            >>> user = await get_current_user(request)
            >>> token = context_manager.set_user(user)
        """
        return _user_ctx.set(user)

    def set_tenant(self, tenant_id: str) -> None:
        """
        Set current tenant in context (called by multi-tenant middleware).
        """
        _tenant_id_ctx.set(tenant_id)

        # Sync with internal tenancy context for ORM isolation
        from eden.tenancy.context import _tenant_ctx
        _tenant_ctx.set(tenant_id)

    def get_app(self) -> Any:
        """
        Get current app instance from context.

        Returns:
            App instance or None if not set (shouldn't happen in request context)
        """
        return _app_ctx.get(None)

    def get_request(self) -> Optional["Request"]:
        """
        Get current request from context.

        Returns:
            Starlette Request or None if not in request context
        """
        return _request_ctx.get(None)

    def get_user(self) -> Any:
        """
        Get current user from context.

        Returns:
            User object or None if not authenticated or not set
        """
        return _user_ctx.get(None)

    def get_tenant_id(self) -> Optional[str]:
        """
        Get current tenant ID from context.

        Returns:
            Tenant ID string or None if not in multi-tenant context
        """
        return _tenant_id_ctx.get(None)

    def get_request_id(self) -> str:
        """
        Get current request ID from context.

        Used for logging correlation and tracing requests across services.

        Returns:
            Request ID (UUID string) or empty string if not initialized
        """
        return _request_id_ctx.get("")

    async def run_in_context(
        self,
        coro: Callable[..., Awaitable[Any]],
        *args,
        app: Optional[Any] = None,
        request: Optional["Request"] = None,
        user: Optional[Any] = None,
        tenant_id: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """
        Run a coroutine within a set context.

        Useful for background tasks, tests, or manual context setup.

        Args:
            coro: Async function to run
            *args: Positional arguments to pass to coro
            app: App instance to set in context
            request: Request instance to set in context
            user: User instance to set in context
            tenant_id: Tenant ID to set in context
            **kwargs: Keyword arguments to pass to coro

        Returns:
            Result of coro execution

        Example:
            >>> async def my_task(x):
            ...     user = get_user()
            ...     return x + 1
            >>> result = await context_manager.run_in_context(
            ...     my_task, 5, user=current_user
            ... )
        """
        # Save current context
        old_app = _app_ctx.get(None)
        old_request = _request_ctx.get(None)
        old_user = _user_ctx.get(None)
        old_tenant_id = _tenant_id_ctx.get(None)
        old_request_id = _request_id_ctx.get("")

        try:
            # Set new context
            if app is not None:
                _app_ctx.set(app)
            if request is not None:
                _request_ctx.set(request)
            if user is not None:
                _user_ctx.set(user)
            if tenant_id is not None:
                _tenant_id_ctx.set(tenant_id)
            
            # Generate a new request_id for the inner context
            _request_id_ctx.set(str(uuid.uuid4()))

            # Run coro with new context
            return await coro(*args, **kwargs)

        finally:
            # Restore old context
            _app_ctx.set(old_app)
            _request_ctx.set(old_request)
            _user_ctx.set(old_user)
            _tenant_id_ctx.set(old_tenant_id)
            _request_id_ctx.set(old_request_id)


# Global singleton instance
context_manager = ContextManager()


# Legacy token-based API (deprecated but kept for backward compatibility)
def set_request(request: "Request") -> contextvars.Token:
    """Set the current request in context (legacy API)."""
    return _request_ctx.set(request)


def reset_request(token: contextvars.Token) -> None:
    """Reset the request context (legacy API)."""
    _request_ctx.reset(token)


def reset_user(token: contextvars.Token) -> None:
    """Reset the user context (legacy API)."""
    _user_ctx.reset(token)


# Convenience accessor functions (use these throughout codebase)
def get_request() -> Optional["Request"]:
    """Get the current request from context."""
    return context_manager.get_request()


def get_user() -> Any:
    """Get the current user from context."""
    return context_manager.get_user()


def set_user(user: Any) -> contextvars.Token:
    """Set the current user in context (called by auth middleware)."""
    return context_manager.set_user(user)


def set_current_user(user: Any) -> contextvars.Token:
    """Alias for set_user."""
    return set_user(user)


def set_app(app: Any) -> None:
    """Set the current app in context."""
    _app_ctx.set(app)


def get_app() -> Any:
    """Get the current app from context."""
    return context_manager.get_app()


def get_tenant_id() -> Optional[str]:
    """Get current tenant ID or None."""
    return context_manager.get_tenant_id()


def set_tenant(tenant_id: str) -> None:
    """Set current tenant ID."""
    context_manager.set_tenant(tenant_id)


def set_current_tenant_id(tenant_id: str) -> None:
    """Alias for set_tenant."""
    return set_tenant(tenant_id)


def get_request_id() -> str:
    """Get current request correlation ID (UUID string)."""
    return context_manager.get_request_id()


def set_request_id(request_id: str) -> contextvars.Token:
    """Set current request correlation ID."""
    return _request_id_ctx.set(request_id)


def reset_request_id(token: contextvars.Token) -> None:
    """Reset the request ID context (legacy API)."""
    _request_id_ctx.reset(token)


class ContextProxy:
    """
    Proxy object that redirects attribute access to the current context-local object.
    Similar to Flask's 'request' or 'session' objects.

    Raises RuntimeError if accessed outside of context (e.g., outside request handler).
    """

    def __init__(self, getter, name):
        self._getter = getter
        self._name = name

    def __getattr__(self, name):
        obj = self._getter()
        if obj is None:
            raise RuntimeError(f"Working outside of {self._name} context.")
        return getattr(obj, name)

    def __setattr__(self, name, value):
        if name in ("_getter", "_name"):
            super().__setattr__(name, value)
        else:
            obj = self._getter()
            if obj is None:
                raise RuntimeError(f"Working outside of {self._name} context.")
            setattr(obj, name, value)

    def __bool__(self):
        return bool(self._getter())

    def __repr__(self):
        obj = self._getter()
        return repr(obj) if obj else f"<unbound {self._name} proxy>"


# Global proxies (deprecated but kept for backward compatibility)
request = ContextProxy(get_request, "request")
user = ContextProxy(get_user, "user")


def is_active(request: Optional[Any], url: str) -> bool:
    """
    Helper to check if a URL or route is currently active (matches current request path).
    Supports exact route names, wildcard sections ('admin:*'), and literal URL paths.
    
    Args:
        request: Request object (optional, defaults to context)
        url: URL string or route name to check
        
    Returns:
        bool: True if active, False otherwise
    """
    if request is None:
        request = get_request()
    
    if not request:
        return False
        
    try:
        current_path = request.url.path.rstrip("/") or "/"
        target_path = url
        
        # 1. Handle wildcard section (e.g., 'admin:*')
        is_wildcard = target_path.endswith("*")
        if is_wildcard:
            target_path = target_path[:-1].rstrip(":_")

        # 2. Try to resolve route name if it doesn't look like a path
        if "/" not in target_path and target_path != "":
            try:
                # Support both 'auth:login' and 'auth_login' style route names
                name = target_path.replace(":", "_")
                resolved = str(request.url_for(name)).rstrip("/") or "/"
                target_path = resolved
            except Exception:
                # Fallback to literal if resolution fails
                pass
        
        # 3. Path normalization for literal paths or resolved routes
        if "://" in target_path:
            from urllib.parse import urlparse
            target_path = urlparse(target_path).path
        
        target_path = target_path.rstrip("/") or "/"
        
        # 4. Perform matching
        if is_wildcard:
            # Matches if it's either the exact base path or starts with base path followed by /
            return current_path == target_path or current_path.startswith(target_path + "/")
            
        return current_path == target_path
    except Exception:
        return False
