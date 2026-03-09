"""
Eden — Dependency Injection

FastAPI-style dependency injection with support for:
- Simple callable dependencies
- Async generator dependencies (yield-based cleanup)
- Nested sub-dependencies
- Per-request caching (each dep resolved once per request)
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any

from eden.requests import Request


class Depends:
    """
    Dependency injection marker.

    Usage:
        async def get_db():
            db = await connect()
            try:
                yield db
            finally:
                await db.close()

        @app.get("/items")
        async def list_items(db=Depends(get_db)):
            ...
    """

    def __init__(self, dependency: Callable[..., Any], *, use_cache: bool = True) -> None:
        self.dependency = dependency
        self.use_cache = use_cache

    def __repr__(self) -> str:
        return f"Depends({self.dependency.__name__})"


class DependencyResolver:
    """
    Resolves a dependency tree for a given route handler.

    Features:
    - Inspects function signatures to find `Depends` defaults
    - Resolves sub-dependencies recursively
    - Caches resolved values per-request to avoid duplicate calls
    - Supports both sync and async callables
    - Supports generator/async-generator deps for cleanup
    """

    def __init__(self) -> None:
        self._cache: dict[Callable, Any] = {}
        self._cleanup_stack: list[Any] = []

    async def resolve(
        self,
        func: Callable[..., Any],
        path_params: dict[str, Any] | None = None,
        request: Any = None,
    ) -> dict[str, Any]:
        """
        Resolve all dependencies for a function and return kwargs.

        Args:
            func: The route handler or dependency function.
            path_params: URL path parameters to inject.
            request: The incoming Request object.

        Returns:
            Dictionary of parameter names to resolved values.
        """
        self._current_path_params = path_params or {}
        sig = inspect.signature(func)
        kwargs: dict[str, Any] = {}

        for name, param in sig.parameters.items():
            # Inject request object
            if name == "request" or param.annotation is Request:
                kwargs[name] = request
                continue

            # Inject application state
            if name == "state":
                kwargs[name] = getattr(request.app, "state", None) if request else None
                continue

            # Inject app instance
            if name == "app":
                kwargs[name] = getattr(request, "app", None) if request else None
                continue

            # Inject path parameters
            if path_params and name in path_params:
                # Attempt type coercion based on annotation
                value = path_params[name]
                annotation = param.annotation
                if annotation != inspect.Parameter.empty and annotation is not str:
                    try:
                        value = annotation(value)
                    except (ValueError, TypeError):
                        pass
                kwargs[name] = value
                continue

            # Resolve Depends() markers
            if isinstance(param.default, Depends):
                dep = param.default
                kwargs[name] = await self._resolve_dependency(dep, request=request)
                continue

        return kwargs

    async def _resolve_dependency(
        self,
        dep: Depends,
        request: Any = None,
    ) -> Any:
        """Resolve a single dependency, with caching and sub-dependency support."""
        callable_fn = dep.dependency

        # Check cache
        if dep.use_cache and callable_fn in self._cache:
            return self._cache[callable_fn]

        # Resolve sub-dependencies of this dependency
        sub_kwargs = await self.resolve(callable_fn, path_params=getattr(self, "_current_path_params", {}), request=request)

        # Call the dependency
        result = callable_fn(**sub_kwargs)

        # Handle async generators (async def with yield)
        if inspect.isasyncgen(result):
            value = await result.__anext__()
            self._cleanup_stack.append(("async_gen", result))
        # Handle sync generators (def with yield)
        elif inspect.isgenerator(result):
            value = next(result)
            self._cleanup_stack.append(("sync_gen", result))
        # Handle coroutines (async def without yield)
        elif inspect.isawaitable(result):
            value = await result
        else:
            value = result

        # Cache the resolved value
        if dep.use_cache:
            self._cache[callable_fn] = value

        return value

    async def cleanup(self) -> None:
        """Run cleanup for all generator-based dependencies (in reverse order)."""
        for kind, gen in reversed(self._cleanup_stack):
            try:
                if kind == "async_gen":
                    try:
                        await gen.__anext__()
                    except StopAsyncIteration:
                        pass
                elif kind == "sync_gen":
                    try:
                        next(gen)
                    except StopIteration:
                        pass
            except Exception:
                # Suppress cleanup errors (log in production)
                pass
        self._cleanup_stack.clear()
        self._cache.clear()
