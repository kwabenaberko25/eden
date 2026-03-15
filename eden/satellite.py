"""
Eden Satellite — Lightweight ASGI Core

A stripped-down, high-performance version of the Eden framework designed
for edge computing, microservices, and serverless environments.
"""

from __future__ import annotations

import inspect
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import Any

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.types import Receive, Scope, Send

from eden.routing import Router
from eden.middleware import get_middleware_class
from eden.exceptions import EdenException


class EdenSatellite(Router):
    """
    The Eden Satellite application.

    A lightweight ASGI application core inherited from Router. 
    It focuses on routing and dependency injection with minimal overhead,
    avoiding the "auto-loading" of heavy features found in the full Eden class.

    Usage:
        app = EdenSatellite()

        @app.get("/")
        async def index():
            return {"status": "online", "mode": "satellite"}
    """

    def __init__(
        self,
        title: str = "Eden Satellite",
        version: str = "0.1.0",
        debug: bool = False,
    ) -> None:
        super().__init__()
        self.title = title
        self.version = version
        self.debug = debug
        
        self._middleware_stack: list[tuple[type, dict[str, Any]]] = []
        self._exception_handlers: dict[type, Callable] = {}
        self._startup_handlers: list[Callable] = []
        self._shutdown_handlers: list[Callable] = []
        
        # Lazy-built ASGI app
        self._app: Starlette | None = None
        self._components: dict[str, Any] = {}

    def add_component(self, name: str, component: Any) -> None:
        """
        Register a modular component (e.g. storage, templates).
        
        This allows Eden Satellite to remain lightweight by only including
        what is explicitly needed for a specific edge deployment.
        """
        self._components[name] = component
        setattr(self, name, component)

    def add_middleware(self, middleware: str | type, **kwargs: Any) -> None:
        """
        Add middleware to the satellite.
        
        Raises:
            RuntimeError: If middleware ordering violates critical dependencies.
        
        CRITICAL ORDERING RULES:
            ⚠️  SessionMiddleware MUST be added before CSRFMiddleware
            ⚠️  SessionMiddleware MUST be added before MessageMiddleware
            
        See: eden.middleware.MIDDLEWARE_EXECUTION_ORDER for full documentation
        """
        if isinstance(middleware, str):
            cls = get_middleware_class(middleware)
            middleware_name = middleware
        else:
            cls = middleware
            middleware_name = getattr(cls, "__name__", str(cls))
        
        # Validate critical middleware ordering
        # Get names of already-added middleware by checking class names
        added_middleware_names = set()
        for cls_item, _ in self._middleware_stack:
            name = getattr(cls_item, "__name__", str(cls_item))
            added_middleware_names.add(name)
        
        # SessionMiddleware MUST come before CSRF and Messages
        if middleware_name == "csrf" and "SessionMiddleware" not in added_middleware_names:
            raise RuntimeError(
                "❌ CRITICAL: CSRFMiddleware requires SessionMiddleware to be added first!\n\n"
                "Solution: Call add_middleware('session') before add_middleware('csrf')\n\n"
                "Why: CSRF tokens are stored in the session. Without SessionMiddleware,\n"
                "     CSRF protection silently fails (major security hole!).\n\n"
                "Recommended: See eden.middleware.MIDDLEWARE_EXECUTION_ORDER for guidance."
            )
        
        if middleware_name == "MessageMiddleware" and "SessionMiddleware" not in added_middleware_names:
            raise RuntimeError(
                "❌ CRITICAL: MessageMiddleware requires SessionMiddleware to be added first!\n\n"
                "Solution: Call add_middleware('session') before using MessageMiddleware\n\n"
                "Why: Messages are stored in the session. Without SessionMiddleware,\n"
                "     the messages feature is non-functional.\n\n"
                "Recommended: See eden.middleware.MIDDLEWARE_EXECUTION_ORDER for guidance."
            )
        
        self._middleware_stack.append((cls, kwargs))

    def on_startup(self, func: Callable) -> Callable:
        """Register a startup handler."""
        self._startup_handlers.append(func)
        return func

    def on_shutdown(self, func: Callable) -> Callable:
        """Register a shutdown handler."""
        self._shutdown_handlers.append(func)
        return func

    async def build(self) -> Starlette:
        """Build the minimal Starlette ASGI application."""
        if self._app is not None:
            return self._app

        # Satellite uses the inherited Router to generate Starlette routes
        starlette_routes = self.to_starlette_routes()

        # Build middleware list
        middleware = [
            Middleware(cls, **kwargs) for cls, kwargs in self._middleware_stack
        ]

        # Lifespan management
        @asynccontextmanager
        async def lifespan(app: Starlette) -> AsyncGenerator[None, None]:
            for handler in self._startup_handlers:
                result = handler()
                if inspect.isawaitable(result):
                    await result
            yield
            for handler in self._shutdown_handlers:
                result = handler()
                if inspect.isawaitable(result):
                    await result

        self._app = Starlette(
            debug=self.debug,
            routes=starlette_routes,
            middleware=middleware,
            exception_handlers=self._exception_handlers,
            lifespan=lifespan,
        )
        return self._app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """The ASGI interface."""
        app = await self.build()
        await app(scope, receive, send)
