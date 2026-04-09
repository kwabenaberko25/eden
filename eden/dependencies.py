from __future__ import annotations
"""
Eden — Dependency Injection

FastAPI-style dependency injection with support for:
- Simple callable dependencies
- Async generator dependencies (yield-based cleanup)
- Sync generator dependencies (yield-based cleanup)
- Context manager dependencies (async/sync with handlers)
- Nested sub-dependencies
- Per-request caching (each dep resolved once per request)
- Circular dependency detection
- Lazy loading support
- Type coercion with complex type handling
- Proper async generator cleanup with __aexit__ support
"""


import contextlib
import functools
import inspect
import sys
from collections.abc import Callable
from typing import Any, Union, Optional, Type, get_origin, get_args, TypeVar, AsyncGenerator, Generator

from eden.requests import Request

T = TypeVar("T")


class Depends:
    """
    Dependency injection marker with optional lazy loading.

    Usage:
        # Regular eager dependency (resolved immediately)
        async def get_db():
            db = await connect()
            try:
                yield db
            finally:
                await db.close()

        # Lazy dependency (resolved only if actually used)
        cache_dep = Depends(get_cache, lazy=True)

        @app.get("/items")
        async def list_items(db=Depends(get_db), cache=cache_dep):
            # db resolved immediately
            # cache only resolved if used in function body
            ...

    Args:
        dependency: The callable or generator to resolve.
        use_cache: If True (default), cache resolved value per request.
        lazy: If True, defer resolution until actually needed (not yet fully 
              implemented; for future use). Defaults to False.
    """

    def __init__(
        self, 
        dependency: Callable[..., Any], 
        *, 
        use_cache: bool = True,
        lazy: bool = False
    ) -> None:
        self.dependency = dependency
        self.use_cache = use_cache
        self.lazy = lazy

    def __repr__(self) -> str:
        return f"Depends({self.dependency.__name__})"


def _coerce_type(value: Any, target_type: Any) -> Any:
    """
    Coerce a value to a target type, handling complex types.
    
    Supports:
    - Basic types: str, int, float, bool
    - Optional[T] and Union types
    - Generic types like List, Dict
    - Pydantic models
    - Custom types with __init__
    
    Args:
        value: The value to coerce.
        target_type: The target type annotation.
    
    Returns:
        Coerced value, or original value if coercion fails/not applicable.
    
    Example:
        >>> _coerce_type("123", int)
        123
        >>> _coerce_type(None, Optional[str])
        None
        >>> _coerce_type("hello", str)
        'hello'
    """
    # Get origin and args first for all cases
    origin = get_origin(target_type)
    args = get_args(target_type)
    
    if value is None:
        # Check if None is allowed (Optional/Union with None)
        if origin is Union:
            if type(None) in args:
                return None
        return value
    
    # Handle Optional[T] and Union types BEFORE isinstance check
    if origin is Union:
        # Try each type in the Union
        for arg_type in args:
            if arg_type is type(None):
                continue
            try:
                # Recursive call for Union member
                return _coerce_type(value, arg_type)
            except (ValueError, TypeError):
                continue
        # If all Union types fail, return original
        return value
    
    # Handle booleans properly from strings
    if target_type is bool or origin is bool:
        if isinstance(value, str):
            lower_val = value.lower()
            if lower_val in ("true", "1", "t", "y", "yes", "on"):
                return True
            if lower_val in ("false", "0", "f", "n", "no", "off"):
                return False
        return bool(value)

    # Check if already correct type (but only for non-generic types)
    if origin is None:  # Not a generic type
        try:
            if isinstance(value, target_type):
                return value
        except TypeError:
            pass  # Some special types raise TypeError on isinstance
    
    # Handle List[T], list types
    if origin in (list, type(list)) or target_type is list:
        if isinstance(value, str):
            # Split by comma if it looks like a list
            if "," in value:
                items = [item.strip() for item in value.split(",")]
                if args: # List[T]
                    return [_coerce_type(item, args[0]) for item in items]
                return items
            return [value]
        if isinstance(value, (list, tuple)):
            if args: # List[T]
                return [_coerce_type(item, args[0]) for item in value]
            return list(value)
        return [value]
    
    # Try basic type constructor
    try:
        if origin is None and callable(target_type):
            return target_type(value)
    except (ValueError, TypeError):
        pass
    
    # Try Pydantic model validation if available
    try:
        if hasattr(target_type, "parse_obj"):  # Pydantic v1
            return target_type.parse_obj(value)
        elif hasattr(target_type, "model_validate"):  # Pydantic v2
            return target_type.model_validate(value)
    except Exception as e:
        from eden.logging import get_logger
        get_logger(__name__).error("Silent exception caught: %s", e, exc_info=True)
    
    # Return original value if all coercion attempts fail
    return value


class LazyDependencyProxy:
    """
    A proxy object that defers dependency resolution until an attribute is accessed.
    
    This is returned when Depends(..., lazy=True) is used.
    """
    def __init__(self, resolver: DependencyResolver, dep: Depends, request: Any):
        self._resolver = resolver
        self._dep = dep
        self._request = request
        self._resolved_value = None
        self._is_resolved = False

    async def _ensure_resolved(self) -> Any:
        """Resolve the dependency if not already resolved."""
        if not self._is_resolved:
            # We must force eager resolution now
            self._resolved_value = await self._resolver._resolve_dependency(
                self._dep, 
                request=self._request, 
                force_eager=True
            )
            self._is_resolved = True
        return self._resolved_value

    def __await__(self):
        """Allow awaiting the proxy directly: await dep"""
        return self._ensure_resolved().__await__()

    async def __call__(self, *args, **kwargs):
        """Allow calling the proxy if it wraps a callable."""
        obj = await self._ensure_resolved()
        result = obj(*args, **kwargs)
        if inspect.isawaitable(result):
            return await result
        return result

    def __getattr__(self, name: str) -> Any:
        """
        Access attributes of the resolved value.
        NOTE: This will fail if not yet resolved, as resolution is async.
        """
        if self._is_resolved:
            return getattr(self._resolved_value, name)
        
        raise RuntimeError(
            f"Lazy dependency {self._dep} must be awaited before attribute access. "
            "Use: value = await dep; value.attribute"
        )

    def __repr__(self) -> str:
        status = "resolved" if self._is_resolved else "lazy"
        return f"<LazyProxy[{status}]: {self._dep}>"


class DependencyResolver:
    """
    Resolves a dependency tree for a given route handler.

    Features:
    - Inspects function signatures to find `Depends` defaults
    - Resolves sub-dependencies recursively
    - Detects circular dependencies and raises CircularDependencyError
    - Caches resolved values per-request to avoid duplicate calls
    - Supports both sync and async callables
    - Supports generator/async-generator deps for cleanup
    - Supports context managers (async with/with statements)
    - Advanced type coercion with Union, Optional, and complex types
    - Proper cleanup of async context managers with __aexit__

    Attributes:
        _cache: Maps callables to their resolved values (per-request).
        _cleanup_stack: List of (kind, obj) tuples for cleanup in reverse order.
        _resolution_stack: Stack of callables being resolved (for circular detection).
    """

    def __init__(self) -> None:
        self._cache: dict[Callable, Any] = {}
        self._cleanup_stack: list[tuple[str, Any]] = []
        self._resolution_stack: list[Callable] = []

    async def __aenter__(self) -> DependencyResolver:
        """Allow using DependencyResolver as an async context manager for automatic cleanup."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Automatically calls cleanup() when exiting the context."""
        await self.cleanup()

    def _check_circular_dependency(self, fn: Callable) -> None:
        """
        Check if a dependency is already being resolved (circular reference).
        """
        if fn in self._resolution_stack:
            chain = [f.__name__ if hasattr(f, "__name__") else str(f) for f in self._resolution_stack] + [fn.__name__ if hasattr(fn, "__name__") else str(fn)]
            chain_str = " -> ".join(chain)
            raise CircularDependencyError(
                f"Circular dependency detected: {chain_str}"
            )

    def _push_resolution(self, fn: Callable) -> None:
        """Add a callable to the resolution stack."""
        self._resolution_stack.append(fn)

    def _pop_resolution(self, fn: Callable) -> None:
        """Remove a callable from the resolution stack."""
        if self._resolution_stack:
             # We search for it to be safe in case of nested resolve calls
             if fn in self._resolution_stack:
                 # Find the index of fn and remove everything from there up (unwinding)
                 idx = self._resolution_stack.index(fn)
                 self._resolution_stack = self._resolution_stack[:idx]

    async def _cleanup_async_context_manager(self, cm: Any) -> None:
        """
        Properly cleanup an async context manager by calling __aexit__.
        
        Args:
            cm: The async context manager to cleanup.
        """
        if hasattr(cm, "__aexit__"):
            try:
                await cm.__aexit__(None, None, None)
            except Exception:
                # Suppress cleanup errors; log in production
                pass

    async def resolve(
        self,
        func: Callable[..., Any],
        path_params: dict[str, Any] | None = None,
        request: Any = None,
        app: Any = None,
    ) -> dict[str, Any]:
        """
        Resolve all dependencies for a function and return kwargs.

        Inspects the function signature and resolves:
        - Built-in injections: request, state, app
        - AsyncSession from context/app state
        - Path parameters (with type coercion)
        - Dependencies marked with Depends()

        Args:
            func: The route handler or dependency function.
            path_params: URL path parameters to inject.
            request: The incoming Request object.

        Returns:
            Dictionary of parameter names to resolved values.

        Raises:
            RuntimeError: If AsyncSession cannot be resolved or accessed outside request context.
            CircularDependencyError: If circular dependency detected.

        Example:
            >>> resolver = DependencyResolver()
            >>> async def get_user(db=Depends(get_db)):
            ...     return await db.query(User).first()
            >>> kwargs = await resolver.resolve(
            ...     get_user, 
            ...     request=request_obj
            ... )
            >>> user = await get_user(**kwargs)
        """
        from sqlalchemy.ext.asyncio import AsyncSession
        from eden.db.session import get_session

        # Use provided app if no request
        if app is None and request:
            app = getattr(request, "app", None)

        self._current_path_params = path_params or {}
        sig = inspect.signature(func)
        kwargs: dict[str, Any] = {}

        for name, param in sig.parameters.items():
            # Resolve Depends() markers FIRST to avoid hijacking reserved names
            if isinstance(param.default, Depends):
                dep = param.default
                kwargs[name] = await self._resolve_dependency(dep, request=request, app=app)
                continue

            # Inject request object
            if name == "request" or param.annotation is Request:
                kwargs[name] = request
                continue

            # Inject current user from context
            if name == "user":
                from eden.context import context_manager
                kwargs[name] = context_manager.get_user()
                continue
            
            # Inject current tenant_id from context
            if name == "tenant_id":
                from eden.context import context_manager
                kwargs[name] = context_manager.get_tenant_id()
                continue

            # Inject application state
            if name == "state":
                kwargs[name] = getattr(app, "state", None) if app else None
                continue

            # Inject app instance
            if name == "app":
                kwargs[name] = app
                continue

            # Inject AsyncSession from context (auto-session acquisition)
            if name == "session" or param.annotation is AsyncSession:
                # Try context first (set by middleware/transaction)
                session = get_session()
                if session is not None:
                    kwargs[name] = session
                    continue
                
                # Fall back to app state database
                if app and hasattr(app, "state") and hasattr(app.state, "db"):
                    db = app.state.db
                    # Create session as a context manager
                    cm = db.session()
                    async_session = await cm.__aenter__()
                    # Store in cleanup stack with proper cleanup method
                    self._cleanup_stack.append(("async_context_manager", cm))
                    kwargs[name] = async_session
                    continue
                
                # No session available
                raise RuntimeError(
                    f"AsyncSession dependency '{name}' could not be resolved. "
                    "Ensure: 1) It's called within a request context with app.state.db set, "
                    "2) It's within an active transaction (db.transaction()), or "
                    "3) Pass the session explicitly."
                )

            # Inject path parameters
            if path_params and name in path_params:
                # Attempt type coercion based on annotation
                value = path_params[name]
                annotation = param.annotation
                if annotation != inspect.Parameter.empty:
                    value = _coerce_type(value, annotation)
                kwargs[name] = value
                continue

        return kwargs

    async def _resolve_dependency(
        self,
        dep: Depends,
        request: Any = None,
        app: Any = None,
        force_eager: bool = False,
    ) -> Any:
        """
        Resolve a single dependency, with caching, sub-dependency support, and circular detection.
        """
        callable_fn = dep.dependency

        # Check Overrides (e.g., from app.dependency_overrides in tests)
        if app and hasattr(app, "dependency_overrides"):
            if callable_fn in app.dependency_overrides:
                callable_fn = app.dependency_overrides[callable_fn]

        # Handle Lazy Loading
        if dep.lazy and not force_eager:
            return LazyDependencyProxy(self, dep, request)

        # Detect circular dependencies
        self._check_circular_dependency(callable_fn)
        self._push_resolution(callable_fn)

        try:
            # Check cache
            if dep.use_cache and callable_fn in self._cache:
                return self._cache[callable_fn]

            # Resolve sub-dependencies of this dependency
            sub_kwargs = await self.resolve(
                callable_fn, 
                path_params=getattr(self, "_current_path_params", {}), 
                request=request,
                app=app
            )

            # Call the dependency
            result = callable_fn(**sub_kwargs)

            # Handle different result types (generators, coroutines, context managers)
            value = await self._resolve_result(result)

            # Cache the resolved value
            if dep.use_cache:
                self._cache[callable_fn] = value

            return value

        finally:
            self._pop_resolution(callable_fn)

    async def _resolve_result(self, result: Any) -> Any:
        """
        Resolve the result of a dependency call, handling:
        - Async generators (async def with yield)
        - Sync generators (def with yield)
        - Coroutines (async def without yield)
        - Context managers (async with support)
        - Regular values

        Args:
            result: The raw result from calling a dependency function.

        Returns:
            The resolved value to inject.
        """
        # Handle async generators (async def with yield)
        if inspect.isasyncgen(result):
            try:
                value = await result.__anext__()
                # Store for cleanup (will call __anext__ again to trigger finally)
                self._cleanup_stack.append(("async_gen", result))
                return value
            except StopAsyncIteration:
                raise ValueError("Async generator dependency yielded no value")

        # Handle sync generators (def with yield)
        elif inspect.isgenerator(result):
            try:
                value = next(result)
                # Store for cleanup (will call next() again to trigger finally)
                self._cleanup_stack.append(("sync_gen", result))
                return value
            except StopIteration:
                raise ValueError("Sync generator dependency yielded no value")

        # Handle coroutines (async def without yield)
        elif inspect.isawaitable(result):
            value = await result
            # Check if the awaited value is an async context manager
            if hasattr(value, "__aenter__") and hasattr(value, "__aexit__"):
                entered = await value.__aenter__()
                self._cleanup_stack.append(("async_context_manager", value))
                return entered
            return value

        # Handle sync context managers (with support)
        elif hasattr(result, "__enter__") and hasattr(result, "__exit__"):
            entered = result.__enter__()
            self._cleanup_stack.append(("sync_context_manager", result))
            return entered

        # Regular value
        else:
            # Check if it's an async context manager that wasn't awaited
            if hasattr(result, "__aenter__") and hasattr(result, "__aexit__"):
                entered = await result.__aenter__()
                self._cleanup_stack.append(("async_context_manager", result))
                return entered
            return result

    async def cleanup(self) -> None:
        """
        Run cleanup for all generator-based and context manager dependencies (in reverse order).

        Handles:
        - Async generators (calls __anext__ to trigger finally block)
        - Sync generators (calls next() to trigger finally block)
        - Async context managers (calls __aexit__)
        - Sync context managers (calls __exit__)

        Errors during cleanup are suppressed to ensure all resources are cleaned up.
        In production, these should be logged.

        Example:
            >>> resolver = DependencyResolver()
            >>> kwargs = await resolver.resolve(handler, request=req)
            >>> try:
            ...     result = await handler(**kwargs)
            ... finally:
            ...     await resolver.cleanup()
        """
        # Process cleanup stack in reverse order (LIFO)
        for kind, obj in reversed(self._cleanup_stack):
            try:
                if kind == "async_gen":
                    # Async generator: calling __anext__ again triggers finally block
                    try:
                        await obj.__anext__()
                    except StopAsyncIteration:
                        # Expected: generator is exhausted
                        pass
                    except Exception as e:
                        from eden.logging import get_logger
                        get_logger("eden.dependencies").error(
                            "Async generator cleanup failed for %s: %s",
                            getattr(obj, '__qualname__', repr(obj)), e,
                            exc_info=True
                        )

                elif kind == "sync_gen":
                    # Sync generator: calling next() again triggers finally block
                    try:
                        next(obj)
                    except StopIteration:
                        # Expected: generator is exhausted
                        pass
                    except Exception as e:
                        from eden.logging import get_logger
                        get_logger("eden.dependencies").error(
                            "Sync generator cleanup failed for %s: %s",
                            getattr(obj, '__qualname__', repr(obj)), e,
                            exc_info=True
                        )

                elif kind == "async_context_manager":
                    # Async context manager: call __aexit__
                    try:
                        await obj.__aexit__(None, None, None)
                    except Exception as e:
                        from eden.logging import get_logger
                        get_logger("eden.dependencies").error(
                            "Async context manager cleanup failed for %s: %s",
                            getattr(obj, '__qualname__', repr(obj)), e,
                            exc_info=True
                        )

                elif kind == "sync_context_manager":
                    # Sync context manager: call __exit__
                    try:
                        obj.__exit__(None, None, None)
                    except Exception as e:
                        from eden.logging import get_logger
                        get_logger("eden.dependencies").error(
                            "Sync context manager cleanup failed for %s: %s",
                            getattr(obj, '__qualname__', repr(obj)), e,
                            exc_info=True
                        )

            except BaseException as e:
                # Catch BaseException to handle CancelledError (Python 3.9+)
                # and TimeoutError during graceful shutdown / client disconnect.
                if isinstance(e, (KeyboardInterrupt, SystemExit)):
                    # Never suppress process-termination signals
                    raise
                from eden.logging import get_logger
                get_logger("eden.dependencies").error(
                    "DI cleanup failed for %s(%s): %s",
                    kind, getattr(obj, '__qualname__', repr(obj)), e,
                    exc_info=True
                )

        # Clear stacks for next request
        self._cleanup_stack.clear()
        self._cache.clear()
        self._resolution_stack.clear()


class DependencyError(Exception):
    """Base class for dependency injection errors."""
    pass


class CircularDependencyError(DependencyError):
    """
    Raised when a circular dependency is detected during resolution.
    """
    pass
