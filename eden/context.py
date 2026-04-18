from __future__ import annotations
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


import contextvars
import logging
import uuid
import contextlib
from typing import TYPE_CHECKING, Any, Optional, Callable, Awaitable, AsyncIterator

if TYPE_CHECKING:
    from eden.requests import Request
    from eden.db.context import EdenDbContext

logger = logging.getLogger(__name__)

# Context variables (one per data type, defined centrally)
_request_ctx: contextvars.ContextVar[Any] = contextvars.ContextVar("eden_request", default=None)
_user_ctx: contextvars.ContextVar[Any] = contextvars.ContextVar("eden_user", default=None)
_app_ctx: contextvars.ContextVar[Any] = contextvars.ContextVar("eden_app", default=None)
_request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("eden_request_id", default="")
_tenant_id_ctx: contextvars.ContextVar[Any] = contextvars.ContextVar("eden_tenant_id", default=None)
_organization_id_ctx: contextvars.ContextVar[Any] = contextvars.ContextVar("eden_organization_id", default=None)
_db_ctx: contextvars.ContextVar[Any] = contextvars.ContextVar("eden_db_ctx", default=None)

# Per-request token storage: each asyncio task gets its own dict of tokens.
# This replaces the old instance-level _tokens dict on ContextManager, which
# was a shared mutable dict that caused cross-request data leakage under
# concurrent ASGI workloads.
_context_tokens: contextvars.ContextVar[dict[str, contextvars.Token] | None] = contextvars.ContextVar(
    "eden_context_tokens", default=None
)


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

    def __init__(self):
        # Token storage is now in the _context_tokens ContextVar (per-request).
        # No instance-level mutable state.
        pass

    def _get_tokens(self) -> dict[str, contextvars.Token]:
        """
        Get the per-request token dictionary, creating one if needed.
        
        Returns:
            A dict that is scoped to the current asyncio task (request).
        """
        tokens = _context_tokens.get(None)
        if tokens is None:
            tokens = {}
            _context_tokens.set(tokens)
        return tokens

    @property
    def ctx(self) -> Optional[EdenDbContext]:
        """
        The Unified Database Context for the current request.
        
        Requires `db.connect()` to have been called.
        """
        return _db_ctx.get(None)

    @contextlib.asynccontextmanager
    async def use_context(self) -> AsyncIterator[EdenDbContext]:
        """
        Async context manager to safely acquire and set the database context locally.
        """
        from eden.db import get_db
        db = get_db()
        async with db.context() as ctx:
            token = _db_ctx.set(ctx)
            try:
                yield ctx
            finally:
                _db_ctx.reset(token)

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
            - Creates a fresh per-request token dict via ContextVar
            - Generates unique request_id for this request (for logging correlation)
            - Sets app and request in context
            - Saves tokens for proper cleanup via reset()
            - User/tenant remain unset until explicitly set by auth/tenancy middleware
            - Each concurrent request gets its own isolated token dict
        """
        # Create a fresh token dict for THIS request's async context
        tokens: dict[str, contextvars.Token] = {}
        _context_tokens.set(tokens)

        # Generate unique request ID for correlation across logs
        request_id = str(uuid.uuid4())

        # Set context vars and save tokens for proper reset on cleanup
        tokens["request_id"] = _request_id_ctx.set(request_id)
        tokens["app"] = _app_ctx.set(app)
        tokens["request"] = _request_ctx.set(request)
        # User and tenant remain None until explicitly set

        logger.debug(
            f"Context initialized: request_id={request_id}, path={request.url.path}"
        )

    async def on_request_end(self) -> None:
        """
        Cleanup context at request end.

        Uses token.reset() to properly revert context vars to their state
        before on_request_start() was called. This is critical for correct
        behavior with asyncio child tasks — set(None) would actively set
        None in the current scope, while reset() properly reverts the value.

        Implementation Notes:
            - Retrieves tokens from the per-request ContextVar (no shared state)
            - Safe to call even if context wasn't initialized
            - Idempotent (multiple calls have same effect)
            - Does NOT raise exceptions; logs warnings instead
        """
        tokens = _context_tokens.get(None)
        
        try:
            # Attempt to reset context vars using saved tokens (proper ContextVar cleanup)
            if tokens is not None:
                # Import tenancy context var for cross-module cleanup
                try:
                    from eden.tenancy.context import _tenant_ctx
                except ImportError:
                    _tenant_ctx = None

                _ctx_var_map = {
                    "request_id": _request_id_ctx,
                    "app": _app_ctx,
                    "request": _request_ctx,
                    "user": _user_ctx,
                    "tenant_id": _tenant_id_ctx,
                    "organization_id": _organization_id_ctx,
                    "tenancy_ctx": _tenant_ctx,  # eden.tenancy.context._tenant_ctx
                    "db_ctx": _db_ctx,
                }
                for key in list(tokens.keys()):
                    token = tokens.pop(key, None)
                    if token is not None:
                        try:
                            ctx_var = _ctx_var_map.get(key)
                            if ctx_var:
                                ctx_var.reset(token)
                        except (ValueError, LookupError):
                            # Token already used or from different context — safe to ignore
                            pass

            # Always explicitly clear context vars to ensure cleanup
            # This is a safety measure in case token resets fail or tokens is None
            _request_id_ctx.set("")
            _app_ctx.set(None)
            _request_ctx.set(None)
            _user_ctx.set(None)
            _tenant_id_ctx.set(None)
            _organization_id_ctx.set(None)
            _db_ctx.set(None)
            try:
                from eden.tenancy.context import _tenant_ctx
                _tenant_ctx.set(None)
            except ImportError:
                pass

            # Clear the per-request token dict itself
            _context_tokens.set(None)

        except Exception as e:
            if hasattr(logger, "warning"):
                logger.warning(f"Error cleaning up context: {e}")

    def clear(self) -> None:
        """
        Forcefully clear all context variables.
        Use with caution, primarily for testing or extreme cleanup scenarios.
        """
        # Set all ContextVars to their default (None) values
        _user_ctx.set(None)
        _tenant_id_ctx.set(None)
        _organization_id_ctx.set(None)
        _app_ctx.set(None)
        _request_ctx.set(None)
        _request_id_ctx.set("")
        _db_ctx.set(None)
        # Clear the per-request token storage
        _context_tokens.set(None)

        try:
            from eden.tenancy.context import _tenant_ctx
            _tenant_ctx.set(None)
        except ImportError:
            pass

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
        token = _user_ctx.set(user)
        # Store token in per-request dict for proper cleanup
        tokens = self._get_tokens()
        tokens["user"] = token
        return token

    def set_tenant(self, tenant_id: str) -> None:
        """
        Set current tenant in context (called by multi-tenant middleware).
        """
        token = _tenant_id_ctx.set(tenant_id)
        # Store token in per-request dict for proper cleanup
        tokens = self._get_tokens()
        tokens["tenant_id"] = token

        # Sync with internal tenancy context for ORM isolation
        # Save the token so on_request_end() can reset it via the token system
        from eden.tenancy.context import _tenant_ctx
        tenancy_token = _tenant_ctx.set(tenant_id)
        tokens["tenancy_ctx"] = tenancy_token

    def set_organization(self, org_id: str) -> None:
        """
        Set current organization in context.
        """
        token = _organization_id_ctx.set(org_id)
        # Store token in per-request dict for proper cleanup
        tokens = self._get_tokens()
        tokens["organization_id"] = token

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

    def get_organization_id(self) -> Optional[str]:
        """
        Get current organization ID from context.

        Returns:
            Organization ID string or None if not set
        """
        return _organization_id_ctx.get(None)

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
        tokens: list[tuple[contextvars.ContextVar[Any], contextvars.Token[Any]]] = []
        try:
            # Set new context and save tokens for safe reset
            if app is not None:
                tokens.append((_app_ctx, _app_ctx.set(app)))
            if request is not None:
                tokens.append((_request_ctx, _request_ctx.set(request)))
            if user is not None:
                tokens.append((_user_ctx, _user_ctx.set(user)))
            if tenant_id is not None:
                tokens.append((_tenant_id_ctx, _tenant_id_ctx.set(tenant_id)))
            
            # Generate a new request_id for the inner context
            tokens.append((_request_id_ctx, _request_id_ctx.set(str(uuid.uuid4()))))

            # Run coro with new context
            return await coro(*args, **kwargs)

        finally:
            # Safely restore old context to garbage-collect mapping mutations
            for ctx_var, token in tokens:
                ctx_var.reset(token)

    def get_context_snapshot(self) -> dict[str, Any]:
        """
        Capture a snapshot of the current context for propagation.
        
        Returns:
            Dictionary containing user, tenant_id, organization_id, and correlation_id.
            Includes any other metadata currently present in context.
        """
        user = self.get_user()
        # Capture raw user if it's a simple ID or the object itself if serializable
        # Most brokers require JSON-serializable labels, so we prefer IDs
        u_id = getattr(user, "id", None) if hasattr(user, "id") else (user if isinstance(user, (str, int)) else None)
        
        return {
            "user_id": u_id,
            "tenant_id": self.get_tenant_id(),
            "organization_id": self.get_organization_id(),
            "correlation_id": self.get_request_id(),
        }

    def restore_context(self, snapshot: dict[str, Any]) -> list[tuple[contextvars.ContextVar, contextvars.Token]]:
        """
        Restore context from a previously captured snapshot.
        
        Args:
            snapshot: Context data to restore.
            
        Returns:
            List of (ContextVar, Token) tuples for resetting the context later.
        """
        tokens = []
        if snapshot.get("correlation_id"):
            tokens.append((_request_id_ctx, _request_id_ctx.set(snapshot["correlation_id"])))
        
        if snapshot.get("tenant_id"):
            tokens.append((_tenant_id_ctx, _tenant_id_ctx.set(snapshot["tenant_id"])))
            # Also sync internal tenancy context if possible
            try:
                from eden.tenancy.context import _tenant_ctx
                tokens.append((_tenant_ctx, _tenant_ctx.set(snapshot["tenant_id"])))
            except ImportError:
                pass
            
        if snapshot.get("organization_id"):
            tokens.append((_organization_id_ctx, _organization_id_ctx.set(snapshot["organization_id"])))
            
        if snapshot.get("user_id"):
            tokens.append((_user_ctx, _user_ctx.set(snapshot["user_id"])))
            
        return tokens

    @contextlib.contextmanager
    def baked_context(self, snapshot: dict[str, Any]) -> Any:
        """
        A context manager that restores a context for the duration of the block
        and cleans it up afterward, even if it was modified inside the block.
        """
        # Save 'before' state for robust revert
        before = {
            "user": self.get_user(),
            "tenant_id": self.get_tenant_id(),
            "org_id": self.get_organization_id(),
            "req_id": self.get_request_id(),
        }
        
        tokens = self.restore_context(snapshot)
        try:
            yield
        finally:
            # 1. Try standard reset (reverse order)
            for ctx_var, token in reversed(tokens):
                try:
                    ctx_var.reset(token)
                except (ValueError, LookupError):
                    # Dirtied context - will be handled by force revert below
                    pass
            
            # 2. Robust Revert: Ensure core values are restored even if dirtied
            # This prevents leakage between task retries
            if _user_ctx.get(None) != before["user"]:
                _user_ctx.set(before["user"])
            if _tenant_id_ctx.get(None) != before["tenant_id"]:
                _tenant_id_ctx.set(before["tenant_id"])
            if _organization_id_ctx.get(None) != before["org_id"]:
                _organization_id_ctx.set(before["org_id"])
            if _request_id_ctx.get(None) != before["req_id"]:
                _request_id_ctx.set(before["req_id"])


# Global singleton instance
context_manager = ContextManager()


# Legacy token-based API (deprecated but kept for backward compatibility)
def set_request(request: "Request") -> contextvars.Token:
    """Set the current request in context (legacy API)."""
    return _request_ctx.set(request)


def reset_request(token: contextvars.Token) -> None:
    """Reset the request context (legacy API)."""
    try:
        _request_ctx.reset(token)
    except ValueError:
        pass
    
    tokens = _context_tokens.get(None)
    if tokens is not None and tokens.get("request") == token:
        tokens.pop("request", None)


def reset_user(token: contextvars.Token) -> None:
    """Reset the user context (legacy API)."""
    try:
        _user_ctx.reset(token)
    except ValueError:
        pass
    
    # Clean up from per-request storage to prevent double-resetting
    tokens = _context_tokens.get(None)
    if tokens is not None and tokens.get("user") == token:
        tokens.pop("user", None)


# Convenience accessor functions (use these throughout codebase)
def get_request() -> Optional["Request"]:
    """Get the current request from context."""
    return context_manager.get_request()


def get_user() -> Any:
    """Get the current user from context."""
    return context_manager.get_user()


def get_context() -> Optional[EdenDbContext]:
    """Get the current database context."""
    return context_manager.ctx


def get_current_user() -> Any:
    """Alias for get_user."""
    return get_user()


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


def get_organization_id() -> Optional[str]:
    """Get current organization ID or None."""
    return context_manager.get_organization_id()


def set_organization(org_id: str) -> None:
    """Set current organization ID."""
    context_manager.set_organization(org_id)


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
        target_path = str(url)
        
        # 1. Handle wildcard section (e.g., 'admin:*')
        is_wildcard = target_path.endswith("*")
        if is_wildcard:
            target_path = target_path.removesuffix("*").rstrip(":_")

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
