from __future__ import annotations
"""
Eden — Routing

Decorator-based router with path parameters, method filtering,
prefix-based grouping, and sub-router composition.
"""


import inspect
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from eden.dependencies import DependencyResolver
from eden.requests import Request
from eden.responses import JsonResponse, HtmlResponse

__all__ = ["Router", "Route", "WebSocketRoute", "View"]

# Canonical HTTP methods supported by class-based views.
# Used by both View.dispatch() and Router.add_view() for consistency.
_VIEW_METHODS = ("get", "post", "put", "patch", "delete", "options", "head")
_ALL_VIEW_METHODS = [m.upper() for m in _VIEW_METHODS]


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
    extras: dict[str, Any] = field(default_factory=dict)

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
            import pydantic
            if isinstance(result, (dict, list, pydantic.BaseModel)):
                return JsonResponse(content=result)
            if isinstance(result, str):
                return HtmlResponse(content=result)
            
            from eden.responses import Response
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

        Looks up a handler method matching the HTTP method (e.g. ``get``, ``post``).
        Falls back to the ``any`` catch-all handler if defined.  When no handler
        matches, raises ``MethodNotAllowed`` with a list of every method this view
        actually implements (consistent with ``Router.add_view``).
        """
        method = request.method.lower()
        handler = getattr(self, method, None)

        if handler is None:
            # Check for generic 'any' handler before failing
            handler = getattr(self, "any", None)

        if handler is None:
            from eden.exceptions import MethodNotAllowed
            # Use _VIEW_METHODS so the reported allowed list matches add_view()
            allowed = [m.upper() for m in _VIEW_METHODS if hasattr(self, m)]
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
            import pydantic
            if isinstance(result, (dict, list, pydantic.BaseModel)):
                return JsonResponse(content=result)
            if isinstance(result, str):
                return HtmlResponse(content=result)
            
            from eden.responses import Response
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
        self._route_index: dict[str, Route | WebSocketRoute] = {}
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

        @self.get("/new", name="new")
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

        @self.get("/{id}/edit", name="edit")
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
        **kwargs: Any,
    ) -> None:
        """Register a route.

        Raises:
            ValueError: If a route with the same *name* already exists on
                this router.  Duplicate names cause ambiguous ``url_for()``
                look-ups and are almost certainly a bug.
        """
        full_path = self.prefix + path
        route_name = name or endpoint.__name__

        # Guard against duplicate route names (C2 / B5)
        for existing in self.routes:
            if isinstance(existing, Route) and existing.name == route_name:
                raise ValueError(
                    f"Route name '{route_name}' already registered for path "
                    f"'{existing.path}'. Cannot register again for '{full_path}'."
                )

        summary = summary
        if not summary:
            doc = inspect.getdoc(endpoint)
            summary = doc.split("\n")[0] if doc else None

        description = description or inspect.getdoc(endpoint)

        route = Route(
            path=full_path,
            endpoint=endpoint,
            methods=methods,
            name=route_name,
            summary=summary,
            description=description,
            tags=(self.tags + (tags or [])),
            middleware=(self.middleware + (middleware or [])),
            include_in_schema=include_in_schema,
            extras=kwargs,
        )
        self.routes.append(route)
        self._route_index[route_name] = route

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
        **kwargs: Any,
    ) -> Callable:
        """General-purpose route decorator."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._add_route(path, func, methods or ["GET"], name, summary, description, tags, middleware, include_in_schema, **kwargs)
            return func

        return decorator

    def get(
        self,
        path: str,
        name: str | None = None,
        middleware: list[Any] | None = None,
        summary: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        include_in_schema: bool = True,
        **kwargs: Any,
    ) -> Callable:
        """Register a GET route."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._add_route(path, func, ["GET"], name, summary, description, tags, middleware, include_in_schema, **kwargs)
            return func

        return decorator

    def post(
        self,
        path: str,
        name: str | None = None,
        middleware: list[Any] | None = None,
        summary: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        include_in_schema: bool = True,
        **kwargs: Any,
    ) -> Callable:
        """Register a POST route."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._add_route(path, func, ["POST"], name, summary, description, tags, middleware, include_in_schema, **kwargs)
            return func

        return decorator

    def put(
        self,
        path: str,
        name: str | None = None,
        middleware: list[Any] | None = None,
        summary: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        include_in_schema: bool = True,
        **kwargs: Any,
    ) -> Callable:
        """Register a PUT route."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._add_route(path, func, ["PUT"], name, summary, description, tags, middleware, include_in_schema, **kwargs)
            return func

        return decorator

    def patch(
        self,
        path: str,
        name: str | None = None,
        middleware: list[Any] | None = None,
        summary: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        include_in_schema: bool = True,
        **kwargs: Any,
    ) -> Callable:
        """Register a PATCH route."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._add_route(path, func, ["PATCH"], name, summary, description, tags, middleware, include_in_schema, **kwargs)
            return func

        return decorator

    def delete(
        self,
        path: str,
        name: str | None = None,
        middleware: list[Any] | None = None,
        summary: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        include_in_schema: bool = True,
        **kwargs: Any,
    ) -> Callable:
        """Register a DELETE route."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._add_route(path, func, ["DELETE"], name, summary, description, tags, middleware, include_in_schema, **kwargs)
            return func

        return decorator

    def options(
        self,
        path: str,
        name: str | None = None,
        middleware: list[Any] | None = None,
        summary: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        include_in_schema: bool = True,
        **kwargs: Any,
    ) -> Callable:
        """Register an OPTIONS route."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._add_route(path, func, ["OPTIONS"], name, summary, description, tags, middleware, include_in_schema, **kwargs)
            return func

        return decorator

    def head(
        self,
        path: str,
        name: str | None = None,
        middleware: list[Any] | None = None,
        summary: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        include_in_schema: bool = True,
        **kwargs: Any,
    ) -> Callable:
        """Register a HEAD route."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._add_route(path, func, ["HEAD"], name, summary, description, tags, middleware, include_in_schema, **kwargs)
            return func

        return decorator

    def validate(self, schema: type[Any], template: str | None = None) -> Callable:
        """Decorator for automatic form validation."""
        import functools
        from eden.forms import BaseForm, Schema
        from eden.responses import JsonResponse, Response

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs) -> Any:
                # Find request in args or kwargs
                request = None
                for arg in args:
                    if hasattr(arg, "scope"):
                        request = arg
                        break
                if not request:
                    request = kwargs.get("request")
                
                if not request:
                    from eden.context import get_request
                    request = get_request()

                # 1. Parse data
                if issubclass(schema, Schema):
                    form = await schema.from_request(request)
                else:
                    # Fallback for plain Pydantic models
                    data = {}
                    try:
                        data = await request.json()
                    except (ValueError, RuntimeError):
                        try:
                            # Use dict() for Starlette/Eden form objects
                            form_data = await request.form()
                            data = dict(form_data)
                        except (ValueError, RuntimeError):
                            pass
                    form = BaseForm(schema=schema, data=data)

                # 2. Validate
                if form.is_valid():
                    sig = inspect.signature(func)
                    # Inject model instance if annotation matches or name is 'credentials'
                    for param_name, param in sig.parameters.items():
                        if param.annotation == schema or param_name == "credentials":
                            kwargs[param_name] = form.model_instance
                            break
                    
                    handler_kwargs = {
                        k: v for k, v in kwargs.items() 
                        if k in sig.parameters
                    }
                    return await func(*args, **handler_kwargs)
                
                # 3. Handle failure
                if template:
                    if "session" in request.scope:
                        request.session["_old_input"] = form.data
                    
                    from eden.templating import render_template
                    return render_template(template, form=form, request=request)
                
                return JsonResponse({"errors": form.errors}, status_code=400)

            return wrapper
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

        The view class should inherit from ``eden.routing.View``.
        Methods like ``get``, ``post``, etc., will be automatically mapped
        to HTTP methods.  If the view defines an ``any`` catch-all method,
        the route is registered for *all* standard HTTP methods.
        """
        view_instance = view_class()

        # Determine supported methods using the shared constant
        has_any = hasattr(view_instance, "any")
        methods = [
            m.upper() for m in _VIEW_METHODS
            if hasattr(view_instance, m)
        ]

        if not methods and not has_any:
            # No explicit handlers — fall back to full set so dispatch()
            # can raise MethodNotAllowed itself.
            methods = list(_ALL_VIEW_METHODS)

        if has_any:
            # "any" means the view accepts every standard method
            methods = list(_ALL_VIEW_METHODS)

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
            if route.name:
                self._route_index[route.name] = route
            return func

        return decorator

    def include_router(self, router: "Router", prefix: str = "", namespace: str = "") -> None:
        """Merge another router's routes into this one, with optional prefix and namespace."""
        combined_prefix = (self.prefix + prefix).rstrip("/")
        router_namespace = namespace or router.name
        
        for route in router.routes:
            # Join prefixes and ensure no double slashes
            new_path = combined_prefix + route.path
            if not new_path.startswith("/"):
                new_path = "/" + new_path
                
            route.path = new_path
            
            # Prepend router namespace to route name if present
            if router_namespace and route.name:
                route.name = f"{router_namespace}:{route.name}"
            
            # Merge middleware
            for m in self.middleware:
                if m not in route.middleware:
                    route.middleware.insert(0, m)
                    
            self.routes.append(route)
            if route.name:
                self._route_index[route.name] = route


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
                    if isinstance(m, Middleware):
                        # Already a Starlette Middleware descriptor — pass through
                        middleware_list.append(m)
                    elif inspect.isclass(m):
                        middleware_list.append(Middleware(m))
                    elif hasattr(m, "__call__") and hasattr(m, "app"):
                        # Callable instance of an ASGI middleware class
                        middleware_list.append(Middleware(type(m)))
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

            # Wrap Eden handler into a Starlette-compatible endpoint.
            # Use Request.from_scope() instead of accessing request._send
            # (a private Starlette attribute) to avoid breakage on upgrades.
            async def endpoint(request: Any, _eden_route=eden_route) -> Any:
                from eden.requests import Request as EdenRequest
                eden_request = EdenRequest.from_scope(
                    request.scope, request.receive, request._send
                )
                path_params = request.path_params
                # Let exceptions bubble up to application-level handlers.
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
        Generate a URL path for a given route name.
        Uses O(1) dictionary lookup and delegates to robust Starlette path parsing.

        Args:
            name: The explicitly registered route name (including namespaces, e.g. "admin:index").
            **path_params: Values to substitute into the path template.

        Returns:
            The fully-interpolated path string (e.g. "/items/42").

        Raises:
            ValueError: If a required path parameter was not provided,
                or if no route matches *name*.
        """
        route = self._route_index.get(name)
        if not route:
            raise ValueError(f"Route named '{name}' not found.")
            
        from starlette.routing import Route as StarletteRoute, WebSocketRoute as StarletteWSRoute
        try:
            if isinstance(route, WebSocketRoute):
                sr = StarletteWSRoute(path=route.path, endpoint=lambda: None, name=name)
            else:
                sr = StarletteRoute(path=route.path, endpoint=lambda: None, name=name)
            return str(sr.url_path_for(name, **path_params))
        except Exception as e:
            # Starlette raises NoMatchFound or similar if URL interpolation fails
            raise ValueError(f"Failed to generate URL for route '{name}': {e}")

# RouteResolver removed in favor of native Starlette routing.
