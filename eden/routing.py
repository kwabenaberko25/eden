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

__all__ = ["Router", "Route", "WebSocketRoute", "View"]


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
            from eden.responses import Response
            if isinstance(result, (dict, list)):
                return JsonResponse(content=result)
            if isinstance(result, Response):
                return result
            return result

        finally:
            # Always clean up generator deps
            await resolver.cleanup()


class View:
    """
    Base class for Class-Based Views (CBV).
    
    Handlers are defined as methods (get, post, put, patch, delete).
    Dependency injection is supported on each method.
    
    Usage:
        class MyView(View):
            async def get(self, request: Request, user_id: int):
                return {"user_id": user_id}
                
        router.add_view("/users/{user_id:int}", MyView)
    """

    async def dispatch(self, request: Request, **path_params: Any) -> Any:
        """
        Main entry point for the view. Dispatches to the appropriate method handler.
        """
        method = request.method.lower()
        handler = getattr(self, method, None)
        
        if handler is None:
            # Check for generic 'any' handler before failing
            handler = getattr(self, "any", None)
            
        if handler is None:
            from eden.exceptions import MethodNotAllowed
            allowed = [m.upper() for m in ["get", "post", "put", "patch", "delete"] if hasattr(self, m)]
            raise MethodNotAllowed(detail=f"Method {request.method} not allowed.", extra={"allowed": allowed})

        # Dependency injection for the specific method handler
        resolver = DependencyResolver()
        try:
            kwargs = await resolver.resolve(
                handler,
                path_params=path_params,
                request=request,
            )

            result = handler(**kwargs)
            if inspect.isawaitable(result):
                result = await result
            
            # Auto-wrap return values for consistency with Route.handle
            from eden.responses import Response
            if isinstance(result, (dict, list)):
                return JsonResponse(content=result)
            if isinstance(result, Response):
                return result
            return result
        finally:
            await resolver.cleanup()

    def render(self, template_name: str, context: dict[str, Any] | None = None, **kwargs: Any) -> Any:
        """
        Helper to render a template from within a view.
        """
        from eden.templating import render_template
        ctx = context or {}
        ctx.update(kwargs)
        return render_template(template_name, **ctx)


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
        name: str | None = None,
        tags: list[str] | None = None,
        middleware: list[Any] | None = None,
        model: Any | None = None,
    ) -> None:
        self.prefix = prefix.rstrip("/")
        self.name = name or (model.__tablename__ if model else None)
        self.tags = tags or []
        self.middleware = middleware or []
        self.routes: list[Route | WebSocketRoute] = []
        if model:
            self._generate_crud_routes(model)

    def _generate_crud_routes(self, model: Any) -> None:
        """
        Auto-generates standard CRUD routes for a given ORM Model.
        """
        from eden.responses import redirect
        from eden.exceptions import NotFound

        # Use explicitly provided prefix or tablename
        prefix = getattr(model, "template_prefix", model.__tablename__.replace("_", "-"))
        
        @self.get("", name="list")
        async def list_items(request: Request):
            items = await model.all()
            return request.render(f"{prefix}/list.html", {"items": items})

        @self.get("/new", name="create")
        async def new_item(request: Request):
            return request.render(f"{prefix}/form.html", {"item": None})

        @self.post("", name="create")
        async def create_item(request: Request):
            data = await request.form_data()
            item = model(**data)
            if await item.save():
                return redirect(f"{self.prefix}/{item.id}")
            return request.render(f"{prefix}/form.html", {"item": item, "errors": item.errors})

        @self.get("/{id}", name="show")
        async def show_item(request: Request, id: str):
            item = await model.get(id)
            if not item:
                raise NotFound(detail=f"{model.__name__} not found.")
            return request.render(f"{prefix}/show.html", {"item": item})

        @self.get("/{id}/edit", name="update")
        async def edit_item(request: Request, id: str):
            item = await model.get(id)
            if not item:
                raise NotFound(detail=f"{model.__name__} not found.")
            return request.render(f"{prefix}/form.html", {"item": item})

        @self.post("/{id}", name="update")
        async def update_item(request: Request, id: str):
            item = await model.get(id)
            if not item:
                raise NotFound(detail=f"{model.__name__} not found.")
            data = await request.form_data()
            if await item.update(**data):
                return redirect(f"{self.prefix}/{item.id}")
            return request.render(f"{prefix}/form.html", {"item": item, "errors": item.errors})

        @self.delete("/{id}", name="destroy")
        async def delete_item(request: Request, id: str):
            item = await model.get(id)
            if not item:
                raise NotFound(detail=f"{model.__name__} not found.")
            await item.delete()
            return redirect(self.prefix)

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
        summary = summary
        if not summary:
            doc = inspect.getdoc(endpoint)
            summary = doc.split("\n")[0] if doc else None
            
        description = description or inspect.getdoc(endpoint)

        route = Route(
            path=full_path,
            endpoint=endpoint,
            methods=methods,
            name=name or endpoint.__name__,
            summary=summary,
            description=description,
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

    def add_view(
        self,
        path: str,
        view_class: type[View],
        name: str | None = None,
        middleware: list[Any] | None = None,
        summary: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        include_in_schema: bool = True,
    ) -> None:
        """
        Register a Class-Based View (CBV).
        
        The view class should inherit from `eden.routing.View`.
        Methods like `get`, `post`, etc., will be automatically mapped to HTTP methods.
        """
        view_instance = view_class()
        
        # Determine supported methods
        methods = [
            m.upper() for m in ["get", "post", "put", "patch", "delete", "options", "head", "any"]
            if hasattr(view_instance, m)
        ]
        
        if not methods:
            # If no methods defined explicitly, assume dispatch handles it (special cases)
            methods = ["GET", "POST", "PUT", "PATCH", "DELETE"]

        if "ANY" in methods:
            methods = ["GET", "POST", "PUT", "PATCH", "DELETE"]
            
        summary = summary
        if not summary:
            doc = inspect.getdoc(view_class)
            summary = doc.split("\n")[0] if doc else None
            
        self._add_route(
            path=path,
            endpoint=view_instance.dispatch,
            methods=methods,
            name=name or view_class.__name__.replace("View", "").lower(),
            summary=summary,
            description=description or inspect.getdoc(view_class),
            tags=tags,
            middleware=middleware,
            include_in_schema=include_in_schema,
        )

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

    def include_router(self, router: "Router", prefix: str = "") -> None:
        """Merge another router's routes into this one."""
        prefix = prefix.rstrip("/")
        for route in router.routes:
            # Join prefixes and ensure no double slashes
            new_path = prefix + route.path
            if not new_path.startswith("/"):
                new_path = "/" + new_path
                
            route.path = new_path
            
            # Prepend router name to route name if present
            if router.name and route.name:
                route.name = f"{router.name}:{route.name}"
            
            # Merge middleware
            for m in self.middleware:
                if m not in route.middleware:
                    route.middleware.insert(0, m)
                    
            self.routes.append(route)


    def to_starlette_routes(self) -> list[Any]:
        """Convert Eden routes to Starlette-compatible Route objects."""
        from starlette.middleware import Middleware
        from starlette.routing import Route as StarletteRoute, WebSocketRoute as StarletteWebSocketRoute
        from eden.middleware import EdenFunctionMiddleware

        starlette_routes = []
        for eden_route in self.routes:
            path = eden_route.path

            # Process middleware: wrap functions in EdenFunctionMiddleware
            middleware_list = []
            if eden_route.middleware:
                for m in eden_route.middleware:
                    if inspect.isclass(m):
                        middleware_list.append(Middleware(m))
                    elif callable(m):
                        middleware_list.append(Middleware(EdenFunctionMiddleware, handler=m))
                    else:
                        middleware_list.append(Middleware(m))

            if isinstance(eden_route, WebSocketRoute):
                # Handle WebSocketRoute
                starlette_routes.append(
                    StarletteWebSocketRoute(
                        path=path,
                        endpoint=eden_route.endpoint,
                        name=eden_route.name,
                        middleware=middleware_list if middleware_list else None
                    )
                )
                continue

            # Wrap Eden handler into a Starlette-compatible endpoint
            async def endpoint(request: Any, _eden_route=eden_route) -> Any:
                from eden.requests import Request
                eden_request = Request(request.scope, request.receive, request._send)
                # Extract path params from Starlette request
                path_params = request.path_params
                # Do not intercept or handle exceptions here; let them bubble up to
                # the application-level handlers registered in `Eden.build`. This
                # keeps routing code simple and avoids accidentally calling
                # methods on the Router instance that it doesn't have.
                return await _eden_route.handle(eden_request, **path_params)

            # Copy rate limit metadata from original endpoint to the Starlette wrapper
            if hasattr(eden_route.endpoint, "_rate_limit"):
                endpoint._rate_limit = eden_route.endpoint._rate_limit
            if hasattr(eden_route.endpoint, "_rate_limit_key"):
                endpoint._rate_limit_key = eden_route.endpoint._rate_limit_key

            starlette_routes.append(
                StarletteRoute(
                    path=path,
                    endpoint=endpoint,
                    methods=eden_route.methods,
                    name=eden_route.name,
                    middleware=middleware_list if middleware_list else None
                )
            )
        return starlette_routes



    def url_for(self, name: str, **path_params: Any) -> str:
        """
        Generate a URL for a given route name.
        """
        import re
        for route in self.routes:
            if route.name == name:
                path = route.path
                # Handle path parameters like {name} or {name:type}
                for param, value in path_params.items():
                    # Simple {param}
                    path = path.replace(f"{{{param}}}", str(value))
                    # {param:type}
                    path = re.sub(rf"{{{param}:.*?}}", str(value), path)
                
                # Check if any parameters are left un-interpolated
                if "{" in path:
                    remaining = re.findall(r"{(.*?)}", path)
                    # Filter out ones that were actually passed (re.sub might have missed if type was different)
                    # but usually it's better to just error if missing params
                    # raise ValueError(f"Missing path parameters for route '{name}': {remaining}")
                    pass
                return path
        
        # Search in sub-router naming convention (router:name)
        if ":" not in name:
            for route in self.routes:
                if route.name and route.name.split(":")[-1] == name:
                    return self.url_for(route.name, **path_params)

        raise ValueError(f"Route with name '{name}' not found")

# RouteResolver removed in favor of native Starlette routing.
