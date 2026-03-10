"""
Eden — Routing

Decorator-based router with path parameters, method filtering,
prefix-based grouping, and sub-router composition.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from eden.dependencies import DependencyResolver
from eden.requests import Request
from eden.responses import JsonResponse

__all__ = ["Router", "Route", "WebSocketRoute"]


@dataclass
class Route:
    """A single route definition."""

    path: str
    endpoint: Callable[..., Any]
    methods: list[str]
    name: str | None = None
    summary: str | None = None
    description: str | None = None
    tags: list[str] = field(default_factory=list)
    middleware: list[Any] = field(default_factory=list)
    include_in_schema: bool = True

    def __post_init__(self) -> None:
        self.methods = [m.upper() for m in self.methods]

    async def handle(self, request: Request, **path_params: Any) -> Any:
        """
        Invoke the handler for an incoming request.
        Handles dependency injection and response serialization.
        """
        # Create a per-request dependency resolver
        resolver = DependencyResolver()

        try:
            # Resolve dependencies
            kwargs = await resolver.resolve(
                self.endpoint,
                path_params=path_params,
                request=request,
            )

            # Call the handler
            result = self.endpoint(**kwargs)
            if inspect.isawaitable(result):
                result = await result

            # Auto-wrap return values
            if isinstance(result, (dict, list)):
                return JsonResponse(content=result)
            return result

        finally:
            # Always clean up generator deps
            await resolver.cleanup()


@dataclass
class WebSocketRoute:
    """A single websocket route definition."""

    path: str
    endpoint: Callable[..., Any]
    name: str | None = None
    middleware: list[Any] = field(default_factory=list)


class Router:
    """
    Decorator-based router with prefix support and sub-router composition.

    Usage:
        router = Router(prefix="/api/v1")

        @router.get("/items")
        async def list_items():
            return {"items": []}

        @router.get("/items/{item_id:int}")
        async def get_item(item_id: int):
            return {"item_id": item_id}

        app.include_router(router)
    """

    def __init__(
        self,
        prefix: str = "",
        tags: list[str] | None = None,
        middleware: list[Any] | None = None,
    ) -> None:
        self.prefix = prefix.rstrip("/")
        self.tags = tags or []
        self.middleware = middleware or []
        self.routes: list[Route | WebSocketRoute] = []

    def add_middleware(self, middleware: Any) -> None:
        """
        Add middleware to all routes in this router.
        
        Usage:
            router.add_middleware(MyMiddleware)
        """
        self.middleware.append(middleware)
        # Apply to existing routes as well
        for route in self.routes:
            if middleware not in route.middleware:
                route.middleware.append(middleware)

    def _add_route(
        self,
        path: str,
        endpoint: Callable[..., Any],
        methods: list[str],
        name: str | None = None,
        summary: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        middleware: list[Any] | None = None,
        include_in_schema: bool = True,
    ) -> None:
        """Register a route."""
        full_path = self.prefix + path
        route = Route(
            path=full_path,
            endpoint=endpoint,
            methods=methods,
            name=name or endpoint.__name__,
            summary=summary or (endpoint.__doc__.strip().split("\n")[0] if endpoint.__doc__ else None),
            description=description or endpoint.__doc__,
            tags=(self.tags + (tags or [])),
            middleware=(self.middleware + (middleware or [])),
            include_in_schema=include_in_schema,
        )
        self.routes.append(route)

    def route(
        self,
        path: str,
        methods: list[str] | None = None,
        name: str | None = None,
        middleware: list[Any] | None = None,
        summary: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        include_in_schema: bool = True,
    ) -> Callable:
        """General-purpose route decorator."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._add_route(path, func, methods or ["GET"], name, summary, description, tags, middleware, include_in_schema)
            return func

        return decorator

    def get(
        self,
        path: str,
        name: str | None = None,
        middleware: list[Any] | None = None,
        summary: str | None = None,
        tags: list[str] | None = None,
        include_in_schema: bool = True,
    ) -> Callable:
        """Register a GET route."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._add_route(path, func, ["GET"], name, summary, None, tags, middleware, include_in_schema)
            return func

        return decorator

    def post(
        self,
        path: str,
        name: str | None = None,
        middleware: list[Any] | None = None,
        summary: str | None = None,
        tags: list[str] | None = None,
        include_in_schema: bool = True,
    ) -> Callable:
        """Register a POST route."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._add_route(path, func, ["POST"], name, summary, None, tags, middleware, include_in_schema)
            return func

        return decorator

    def put(
        self,
        path: str,
        name: str | None = None,
        middleware: list[Any] | None = None,
        summary: str | None = None,
        tags: list[str] | None = None,
        include_in_schema: bool = True,
    ) -> Callable:
        """Register a PUT route."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._add_route(path, func, ["PUT"], name, summary, None, tags, middleware, include_in_schema)
            return func

        return decorator

    def patch(
        self,
        path: str,
        name: str | None = None,
        middleware: list[Any] | None = None,
        summary: str | None = None,
        tags: list[str] | None = None,
        include_in_schema: bool = True,
    ) -> Callable:
        """Register a PATCH route."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._add_route(path, func, ["PATCH"], name, summary, None, tags, middleware, include_in_schema)
            return func

        return decorator

    def delete(
        self,
        path: str,
        name: str | None = None,
        middleware: list[Any] | None = None,
        summary: str | None = None,
        tags: list[str] | None = None,
        include_in_schema: bool = True,
    ) -> Callable:
        """Register a DELETE route."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._add_route(path, func, ["DELETE"], name, summary, None, tags, middleware, include_in_schema)
            return func

        return decorator

    def websocket(
        self,
        path: str,
        name: str | None = None,
        middleware: list[Any] | None = None,
    ) -> Callable:
        """Register a WebSocket route."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            full_path = self.prefix + path
            route = WebSocketRoute(
                path=full_path,
                endpoint=func,
                name=name or func.__name__,
                middleware=(self.middleware + (middleware or [])),
            )
            self.routes.append(route)
            return func

        return decorator

    def include_router(self, router: Router, prefix: str = "") -> None:
        """Merge another router's routes into this one."""
        prefix = prefix.rstrip("/")
        for route in router.routes:
            # Join prefixes and ensure no double slashes
            new_path = prefix + route.path
            if not new_path.startswith("/"):
                new_path = "/" + new_path
                
            route.path = new_path
            
            # Merge middleware
            for m in self.middleware:
                if m not in route.middleware:
                    route.middleware.insert(0, m)
                    
            self.routes.append(route)

    def to_starlette_routes(self) -> list[Any]:
        """Convert Eden routes to Starlette-compatible Route objects."""
        from starlette.middleware import Middleware
        from starlette.routing import Route as StarletteRoute, WebSocketRoute as StarletteWebSocketRoute

        starlette_routes = []
        for eden_route in self.routes:
            path = self.prefix + eden_route.path

            if isinstance(eden_route, WebSocketRoute):
                # Handle WebSocketRoute
                starlette_routes.append(
                    StarletteWebSocketRoute(
                        path=path,
                        endpoint=eden_route.endpoint,
                        name=eden_route.name,
                        # WebSocketRoute in Starlette doesn't support Middleware directly
                        # in the same way as Route in some versions, but we can wrap it if needed.
                    )
                )
                continue

            # Wrap Eden handler into a Starlette-compatible endpoint
            async def endpoint(request: Any, _eden_route=eden_route) -> Any:
                from eden.requests import Request
                eden_request = Request(request.scope, request.receive, request._send)
                # Extract path params from Starlette request
                path_params = request.path_params
                try:
                    return await _eden_route.handle(eden_request, **path_params)
                except Exception as exc:
                    # Capture template errors and redirect to custom page
                    from jinja2.exceptions import TemplateError
                    if isinstance(exc, TemplateError) or "templating" in str(getattr(exc, '__module__', '')):
                         if hasattr(self, "_render_enhanced_template_error"):
                             return await self._render_enhanced_template_error(eden_request, exc)
                    raise exc

            starlette_routes.append(
                StarletteRoute(
                    path=path,
                    endpoint=endpoint,
                    methods=eden_route.methods,
                    name=eden_route.name,
                    middleware=[Middleware(m) for m in eden_route.middleware] if eden_route.middleware else None
                )
            )
        return starlette_routes


# RouteResolver removed in favor of native Starlette routing.
