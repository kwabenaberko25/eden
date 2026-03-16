"""
Eden — Application

The main `Eden` class: your entry point for building an ASGI web application.
Combines routing, middleware, dependency injection, exception handling,
and lifespan management into a clean, decorator-driven API.
"""

from __future__ import annotations

import inspect
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Type, Union
from starlette.applications import Starlette
from starlette.datastructures import State
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware import Middleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

import uvicorn

if TYPE_CHECKING:
    from eden.cache import CacheBackend

import os
import asyncio
import uvicorn
from eden.exceptions import EdenException
from eden.middleware import get_middleware_class
from eden.requests import Request
from eden.responses import HtmlResponse, JsonResponse
from eden.routing import Router
from eden.storage import LocalStorageBackend
from eden.storage import storage as eden_storage
from eden.tasks import EdenBroker, create_broker
from eden.templating import EdenTemplates


class Eden:
    """
    The Eden application.

    A high-level ASGI app that wraps Starlette with an ergonomic,
    decorator-driven API — similar to Flask/FastAPI but with its
    own identity.

    Usage:
        app = Eden()

        @app.get("/")
        async def index():
            return {"message": "Hello, Eden! 🌿"}

        app.run()
    """

    def __init__(
        self,
        title: str = "Eden",
        version: str = "0.1.0",
        debug: bool = False,
        description: str = "",
        secret_key: str = "",
        config: Optional[Any] = None,
    ) -> None:
        from eden.context import set_app
        set_app(self)

        # Load configuration if not provided
        if config is None:
            from eden.config import get_config
            config = get_config()
        
        self.config = config
        
        # Configure from Config object if provided, else use explicit params
        self.title = title or config.title
        self.version = version or config.version
        self.description = description
        self.secret_key = secret_key or config.secret_key
        self.debug = debug if debug else config.debug
        
        self.browser_reload = os.getenv("EDEN_BROWSER_RELOAD", "true").lower() == "true"
        self.template_dir = "templates"
        self.media_dir = "media"
        self.static_dir = "static"
        self.static_url = "/static"

        # Internal routing
        self._router = Router()
        self._middleware_stack: list[tuple[type, dict[str, Any]]] = []
        self._exception_handlers: dict[type, Callable] = {}
        self._startup_handlers: list[Callable] = []
        self._shutdown_handlers: list[Callable] = []

        # Task Queue
        self._raw_broker = create_broker()
        self._eden_broker = EdenBroker(self._raw_broker)
        self._eden_broker.app = self
        self.broker = self._eden_broker

        # Templating
        self._templates: EdenTemplates | None = None

        # Storage
        self.storage = eden_storage
        self.storage.register(
            "local",
            LocalStorageBackend(base_path=self.media_dir, base_url="/media/"),
            default=True
        )

        # Built ASGI app (lazy)
        self._app: Starlette | None = None
        self._build_lock = asyncio.Lock()

        # Health checks
        self.state = State()
        self._health_checks: list[tuple[str, Callable]] = []
        self._health_enabled: bool = False

        # Mail (ConsoleBackend default)
        from eden.mail import ConsoleBackend as _ConsoleBackend
        from eden.mail import configure_mail as _configure_mail
        self.mail = _ConsoleBackend()
        _configure_mail(self.mail)

        # Payments
        self.payments = None

        # Caching
        self.cache: Optional["CacheBackend"] = None

    @classmethod
    def get_current(cls) -> Eden:
        """Get the current active Eden application instance."""
        from eden.context import get_app
        return get_app()




    # ── Health Checks ─────────────────────────────────────────────────────

    def enable_health_checks(
        self,
        health_path: str = "/health",
        ready_path: str = "/ready",
    ) -> None:
        """
        Register /health and /ready endpoints.

        The /health endpoint returns basic app info.
        The /ready endpoint runs all registered readiness checks
        and returns their individual statuses.

        Usage:
            app.enable_health_checks()
            app.add_readiness_check("database", check_db_connection)
        """
        self._health_enabled = True

        @self._router.get(health_path, name="health")
        async def health_check() -> dict:
            return {
                "status": "healthy",
                "app": self.title,
                "version": self.version,
                "description": self.description,
            }

        @self._router.get(ready_path, name="ready")
        async def readiness_check() -> dict:
            import asyncio
            results: dict[str, Any] = {}
            all_ok = True
            for name, check_fn in self._health_checks:
                try:
                    if asyncio.iscoroutinefunction(check_fn):
                        result = await check_fn()
                    else:
                        result = check_fn()
                    results[name] = {"status": "ok"} if result else {"status": "fail"}
                    if not result:
                        all_ok = False
                except Exception as e:
                    results[name] = {"status": "fail", "error": str(e)}
                    all_ok = False

            return {
                "status": "ready" if all_ok else "not_ready",
                "checks": results,
            }

    def add_readiness_check(self, name: str, check_fn: Callable | None = None) -> Callable | None:
        """
        Register a readiness check function.
        Can be used as a direct call or as a decorator.

        The function should return True if the service is ready,
        or raise an exception / return False if not.

        Args:
            name: Human-readable name for the check (e.g., "database").
            check_fn: Sync or async callable that returns a boolean.
        """
        if check_fn is None:
            def decorator(func: Callable) -> Callable:
                self._health_checks.append((name, func))
                return func
            return decorator
            
        self._health_checks.append((name, check_fn))


    # ── Route Decorators ─────────────────────────────────────────────────
    
    def validate(self, schema: Type[Any], template: str | None = None) -> Callable:
        """
        Decorator for automatic form validation.
        
        Args:
            schema: The Schema or Pydantic class to validate against.
            template: Optional template to re-render on failure.
            
        Usage:
            @app.post("/login")
            @app.validate(LoginSchema, template="login.html")
            async def login(credentials: LoginSchema):
                # Only runs if valid
                ...
        """
        import functools
        from eden.forms import BaseForm, Schema

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
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
                    except (ValueError, RuntimeError) as e:
                        # ValueError: invalid JSON
                        # RuntimeError: request body already consumed
                        try:
                            data = dict(await request.form())
                        except (ValueError, RuntimeError):
                            # Form parsing also failed, continue with empty data
                            pass
                    form = BaseForm(schema=schema, data=data)

                # 2. Validate
                if form.is_valid():
                    # 2.1 Prepare arguments for the handler
                    sig = inspect.signature(func)
                    
                    # Inject credentials
                    for param_name, param in sig.parameters.items():
                        if param.annotation == schema or param_name == "credentials":
                            kwargs[param_name] = form.model_instance
                            break
                    
                    # Filter kwargs to only those the handler expects
                    handler_kwargs = {
                        k: v for k, v in kwargs.items() 
                        if k in sig.parameters
                    }
                    
                    return await func(*args, **handler_kwargs)
                
                # 3. Handle failure
                if template:
                    # Save old input for the @old directive
                    if hasattr(request, "session"):
                        request.session["_old_input"] = form.data
                    
                    # Inject form into context
                    return self.render(template, form=form)
                
                # Default JSON error response
                from eden.responses import JsonResponse
                return JsonResponse({"errors": form.errors}, status_code=400)

            return wrapper
        return decorator

    def route(
        self,
        path: str,
        methods: list[str] | None = None,
        name: str | None = None,
        middleware: list[Any] | None = None,
    ) -> Callable:
        """Register a route for any HTTP method(s)."""
        return self._router.route(path, methods=methods, name=name, middleware=middleware)

    def get(self, path: str, **kwargs: Any) -> Callable:
        """Register a GET route."""
        return self._router.get(path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> Callable:
        """Register a POST route."""
        return self._router.post(path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> Callable:
        """Register a PUT route."""
        return self._router.put(path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> Callable:
        """Register a PATCH route."""
        return self._router.patch(path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> Callable:
        """Register a DELETE route."""
        return self._router.delete(path, **kwargs)

    def websocket(self, path: str, **kwargs: Any) -> Callable:
        """Register a WebSocket route."""
        return self._router.websocket(path, **kwargs)

    # ── Task Decorators ──────────────────────────────────────────────────
    # Removed redundant task method to favor property below.

    # ── Templating ───────────────────────────────────────────────────────

    @property
    def templates(self) -> EdenTemplates:
        """Access the templating engine."""
        if self._templates is None:
            directories = [self.template_dir]
            
            # Add built-in framework templates if they exist
            import eden.auth
            auth_templates = os.path.join(os.path.dirname(eden.auth.__file__ or ""), "templates")
            if os.path.isdir(auth_templates):
                directories.append(auth_templates)
                
            self._templates = EdenTemplates(directory=directories)
        return self._templates

    def render(self, template_name: str, context: dict[str, Any] | None = None, **kwargs: Any) -> Any:
        """Short helper to render a template."""
        ctx = context or {}
        ctx.update(kwargs)
        return self.templates.TemplateResponse(template_name, ctx)

    # ── Sub-Router ───────────────────────────────────────────────────────

    def include_router(self, router: Router, prefix: str = "") -> None:
        """Mount a sub-router's routes into this app."""
        self._router.include_router(router, prefix=prefix)

    def add_view(self, path: str, view_class: type[View], **kwargs: Any) -> None:
        """Register a Class-Based View (CBV) at the application level."""
        self._router.add_view(path, view_class, **kwargs)

    def url_for(self, name: str, **path_params: Any) -> str:
        """Generate a URL for a given route name."""
        return self._router.url_for(name, **path_params)

    def get_routes(self) -> list[dict[str, Any]]:
        """
        Returns a list of all registered routes and their metadata.
        Useful for debugging or generating sitemaps.
        """
        routes_info = []
        for route in self._router.routes:
            from eden.routing import WebSocketRoute
            is_ws = isinstance(route, WebSocketRoute)
            routes_info.append({
                "path": route.path,
                "name": route.name,
                "type": "websocket" if is_ws else "http",
                "methods": [] if is_ws else getattr(route, "methods", ["GET"]),
                "summary": getattr(route, "summary", None),
            })
        return routes_info

    # ── SaaS Features ────────────────────────────────────────────────────

    def mount_admin(self, path: str = "/admin", admin_site=None) -> None:
        """
        Mount the admin panel at the given path.

        Usage:
            from eden.admin import admin
            admin.register(User, UserAdmin)
            app.mount_admin()
        """
        from eden.admin import admin as default_admin
        site = admin_site or default_admin
        router = site.build_router(prefix=path)
        self.include_router(router)

    def configure_mail(self, backend) -> None:
        """Set the email backend for this app."""
        from eden.mail import configure_mail as _configure_mail
        self.mail = backend
        _configure_mail(backend)

    def configure_payments(self, provider) -> None:
        """Set the payment provider for this app."""
        self.payments = provider

    @property
    def task(self) -> EdenBroker:
        """Access the task broker as a decorator or utility."""
        return self._eden_broker

    def mount_webhooks(self, path: str = "/webhooks/stripe", webhook_router=None) -> None:
        """Mount the payment webhook endpoint."""
        if webhook_router:
            route = webhook_router.build_route(path)
            self._router.routes.append(route)


    def add_middleware(self, middleware: str | type, **kwargs: Any) -> None:
        """
        Add middleware to the application.

        Args:
            middleware: Either a middleware class or a string shorthand
                        ("cors", "gzip", "session", "csrf").
            **kwargs: Configuration for the middleware.
        
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
        elif not inspect.isclass(middleware) and callable(middleware):
            from eden.middleware import EdenFunctionMiddleware
            cls = EdenFunctionMiddleware
            kwargs = {"handler": middleware, **kwargs}
            middleware_name = getattr(middleware, "__name__", "function_middleware")
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
                "Recommended: Use app.setup_defaults() for quick-start setup."
            )
        
        if middleware_name == "MessageMiddleware" and "SessionMiddleware" not in added_middleware_names:
            raise RuntimeError(
                "❌ CRITICAL: MessageMiddleware requires SessionMiddleware to be added first!\n\n"
                "Solution: Call add_middleware('session') before using MessageMiddleware\n\n"
                "Why: Messages are stored in the session. Without SessionMiddleware,\n"
                "     the messages feature is non-functional.\n\n"
                "Recommended: Use app.setup_defaults() for quick-start setup."
            )
        
        self._middleware_stack.append((cls, kwargs))

    def setup_defaults(self) -> None:
        """
        Quick-start middleware setup.
        
        Adds the most common middleware stack in the correct order:
        1. Security headers (XSS, clickjacking, HSTS protection)
        2. Session management (session cookies, CSRF tokens)
        3. CSRF protection (depends on session)
        4. GZIP compression (transparent response compression)
        5. CORS (cross-origin requests)
        6. Rate limiting (optional, off by default)
        
        This is a convenience method for beginners. Advanced users should
        call add_middleware() explicitly to customize the stack.
        
        Example:
            app = Eden(secret_key="...")
            app.setup_defaults()  # Or explicitly add middleware
            
            # These are equivalent:
            app.add_middleware("security")
            app.add_middleware("session", secret_key=app.secret_key)
            app.add_middleware("csrf")
            app.add_middleware("gzip")
            app.add_middleware("cors", allow_origins=["*"])
        """
        self.add_middleware("security")        # Security headers first
        self.add_middleware("session", secret_key=self.secret_key)
        self.add_middleware("csrf")            # CSRF requires session
        self.add_middleware("gzip")            # Response compression
        self.add_middleware("cors", allow_origins=["*"])  # Allow all origins (configure as needed)

    def setup_tasks(self) -> None:
        """
        Register task broker lifecycle hooks with the app.
        
        This method is optional — the task broker is automatically started/stopped
        with the app's lifespan. Call this only if you need to configure task-specific
        options beyond defaults.
        
        The broker already comes configured with:
        - InMemoryBroker for development (automatically switched to Redis in production)
        - Exponential backoff retry (1s, 2s, 4s, 8s, 16s)
        - Task result storage (7-day TTL by default)
        - Dead-letter queue for permanently failed tasks
        - Automatic periodic task startup/shutdown
        
        Example::
        
            app = Eden()
            app.setup_tasks()  # Optional; not required
            
            @app.task()
            async def send_email(to: str):
                pass
            
            @app.task.every(minutes=5)
            async def refresh_cache():
                pass
            
            await send_email.kiq(to="user@example.com")
        """
        from eden.tasks.lifecycle import setup_task_broker
        setup_task_broker(self)

    # ── Lifespan Hooks ───────────────────────────────────────────────────

    def on_startup(self, func: Callable) -> Callable:
        """Register a startup handler."""
        self._startup_handlers.append(func)
        return func

    def on_shutdown(self, func: Callable) -> Callable:
        """Register a shutdown handler."""
        self._shutdown_handlers.append(func)
        return func

    # ── Exception Handlers ───────────────────────────────────────────────

    def exception_handler(self, exc_class: type) -> Callable:
        """Register a custom exception handler."""

        def decorator(func: Callable) -> Callable:
            self._exception_handlers[exc_class] = func
            return func

        return decorator

    def register_error_handler(self, handler) -> None:
        """
        Register a global error handler (Layer 5-6: Plugin system).
        
        Error handlers are dispatched by ErrorHandlerMiddleware in order of registration.
        First matching handler (where matches() returns True) processes the exception.
        
        Args:
            handler: ErrorHandler instance with matches() and handle() methods
        
        Raises:
            ValueError: If handler doesn't implement the ErrorHandler interface
        
        Example:
            from eden.error_middleware import ErrorHandler
            
            class DatabaseErrorHandler(ErrorHandler):
                def matches(self, exc: Exception) -> bool:
                    return "database" in str(type(exc)).lower()
                
                async def handle(self, exc: Exception, request, app):
                    logger.error(f"Database error: {exc}")
                    return JsonResponse(
                        {"error": "Database error. Please try again."},
                        status_code=500
                    )
            
            app.register_error_handler(DatabaseErrorHandler())
        
        Implementation Notes:
            - Handlers should have matches(exc) → bool and handle(exc, request, app) → Response
            - Handlers are checked in registration order (FIFO)
            - First matching handler is used
            - Can chain handlers by having one re-raise the exception
        """
        from eden.exceptions import error_handler_registry, ErrorHandler
        
        # Validate handler interface
        if not isinstance(handler, ErrorHandler):
            raise ValueError(
                f"Error handler must be an instance of ErrorHandler, got {type(handler)}"
            )
        
        # Register with global registry
        error_handler_registry.register(handler)


    # ── ASGI Interface ───────────────────────────────────────────────────

    async def build(self) -> Starlette:
        """Build the Starlette ASGI application from registered routes and middleware."""
        if self._app is not None:
            return self._app

        async with self._build_lock:
            # Multi-check
            if self._app is not None:
                return self._app

            # Convert Eden routes to Starlette routes
            starlette_routes = self._router.to_starlette_routes()

            # Add system reload WebSocket route if in debug mode
            if self.debug and self.browser_reload:
                from starlette.routing import WebSocketRoute as StarletteWebSocketRoute
                from starlette.websockets import WebSocket

                async def reload_websocket(websocket: WebSocket) -> None:
                    await websocket.accept()
                    try:
                        # Keep connection alive until server restarts or client disconnects
                        while True:
                            await websocket.receive_text()
                    except Exception:
                        # Client disconnected or connection lost (expected)
                        pass

                starlette_routes.insert(0, StarletteWebSocketRoute("/_eden/reload", reload_websocket))

            # Add Real-time Sync WebSocket route
            from starlette.routing import WebSocketRoute as StarletteWebSocketRoute
            from starlette.websockets import WebSocket
            from eden.websocket import connection_manager as manager

            async def sync_websocket(websocket: WebSocket) -> None:
                await manager.connect(websocket)
                try:
                    while True:
                        data = await websocket.receive_json()
                        action = data.get("action")
                        channel = data.get("channel")
                        
                        if action == "subscribe" and channel:
                            await manager.subscribe(websocket, channel)
                        elif action == "unsubscribe" and channel:
                            await manager.unsubscribe(websocket, channel)
                except Exception:
                    # Client disconnected or invalid message (expected)
                    pass
                finally:
                    await manager.disconnect(websocket)

            starlette_routes.insert(0, StarletteWebSocketRoute("/_eden/sync", sync_websocket, name="eden:sync"))

            # Include Component Actions Router
            from eden.components import get_component_router
            comp_router = get_component_router()
            starlette_routes.extend(comp_router.to_starlette_routes())


        # Build middleware list
        middleware = [
            Middleware(cls, **kwargs) for cls, kwargs in self._middleware_stack
        ]

        # Auto-configure database if state.database_url is set
        db_url = getattr(self.state, "database_url", None)
        if db_url:
            from eden.db import Model, init_db
            # Check if already bound to avoid double init
            if not hasattr(Model, "_db") or Model._db is None:
                db = init_db(db_url, self)
                Model._bind_db(db)

                # Connect to DB on startup
                @self.on_startup
                async def _connect_db():
                    # For dev: auto-create tables if URL contains sqlite
                    await db.connect(create_tables="sqlite" in db_url)

        # Auto-configure Redis Cache if REDIS_URL is set
        redis_url = os.environ.get("REDIS_URL") or getattr(self.state, "redis_url", None)
        if redis_url and not self.cache:
            from eden.cache.redis import RedisCache
            self.cache = RedisCache(url=redis_url)
            self.cache.mount(self)

        # Add middleware in correct order (outermost first):
        # 1. ContextMiddleware (OUTERMOST: initializes request context, cleanup, etc.)
        # 2. RequestContextMiddleware (makes request accessible to all downstreams)
        # 3. ErrorHandlerMiddleware (catches exceptions from route handlers)
        from eden.context_middleware import ContextMiddleware
        middleware.insert(0, Middleware(ContextMiddleware))

        # Always include RequestContextMiddleware as the outermost after ContextMiddleware
        # to ensure get_request() works in all other middlewares, views, and templates.
        middleware.insert(1, Middleware(get_middleware_class("request")))

        # Add ErrorHandlerMiddleware early to catch exceptions from all subsequent handlers
        # This must come after ContextMiddleware and RequestContextMiddleware
        from eden.error_middleware import ErrorHandlerMiddleware
        middleware.insert(2, Middleware(ErrorHandlerMiddleware))

        # Add Browser Reload middleware as the INNERMOST layer (after GZip, etc.)
        # so it sees the raw HTML before it gets compressed.
        if self.debug and self.browser_reload:
            middleware.append(Middleware(get_middleware_class("browser_reload")))

        # Prepare exception handlers for Starlette
        exception_handlers = {
            exc_cls: self._wrap_exception_handler(handler)
            for exc_cls, handler in self._exception_handlers.items()
        }

        # Add default handles for EdenException and Exception if not provided
        if EdenException not in exception_handlers:
            exception_handlers[EdenException] = self._handle_eden_exception
        if Exception not in exception_handlers:
            exception_handlers[Exception] = self._handle_unhandled_exception

        # Explicitly register for Jinja2 template errors to override generic exception handling
        from jinja2.exceptions import TemplateError as JinjaTemplateError
        if JinjaTemplateError not in exception_handlers:
            exception_handlers[JinjaTemplateError] = self._render_enhanced_template_error

        # Add handler for Starlette's internal HTTPExceptions (e.g. 404, 405)
        if StarletteHTTPException not in exception_handlers:
            exception_handlers[StarletteHTTPException] = self._handle_starlette_http_exception

        # Add handler for Starlette routing exceptions (e.g. NoMatchFound for missing route names)
        from starlette.routing import NoMatchFound
        if NoMatchFound not in exception_handlers:
            exception_handlers[NoMatchFound] = self._handle_no_match_found

        # Lifespan
        @asynccontextmanager
        async def lifespan(app: Starlette) -> AsyncGenerator[None, None]:
            # Start broker
            await self.broker.startup()
            for handler in self._startup_handlers:
                result = handler()
                if inspect.isawaitable(result):
                    await result
            yield
            # Stop broker
            await self.broker.shutdown()
            for handler in self._shutdown_handlers:
                result = handler()
                if inspect.isawaitable(result):
                    await result

        # Mount static files if the directory exists
        if os.path.isdir(self.static_dir):
            from starlette.routing import Mount
            from starlette.staticfiles import StaticFiles
            starlette_routes.append(
                Mount(self.static_url, app=StaticFiles(directory=self.static_dir), name="static")
            )

        self._app = Starlette(
            debug=self.debug,
            routes=starlette_routes,
            middleware=middleware,
            exception_handlers=exception_handlers,  # type: ignore
            lifespan=lifespan,
        )
        # Synchronize Eden attributes to Starlette app
        self._app.eden = self # type: ignore
        if self.cache:
            self._app.cache = self.cache # type: ignore
            
        return self._app

    def _wrap_exception_handler(self, handler: Callable) -> Callable:
        """Ensure exception handlers receive Eden Request objects."""
        async def wrapped(request: StarletteRequest, exc: Exception) -> StarletteResponse:
            eden_request = Request(request.scope, request.receive, request._send)
            result = handler(eden_request, exc)
            if inspect.isawaitable(result):
                return await result
            return result
        return wrapped

    async def _handle_request(self, request: Request) -> StarletteResponse:
        """
        Original route resolution is now handled by Starlette.
        This method is kept for backwards compatibility or manual calls.
        """
        # Note: If this is called, it might not use the optimized Starlette router!
        # It's better to let Starlette's __call__ handle the request.
        app = await self.build()
        return await app.__call__(request.scope, request.receive, request._send) # type: ignore

    async def _handle_eden_exception(
        self, request: Request, exc: EdenException
    ) -> StarletteResponse:
        """Handle Eden-specific exceptions, with custom handler support."""
        handler = self._exception_handlers.get(type(exc))
        if handler:
            result = handler(request, exc)
            if inspect.isawaitable(result):
                result = await result
            return result

        return self._error_response(
            request=request,
            detail=exc.detail,
            status_code=exc.status_code,
            extra=exc.extra if exc.extra else None,
        )

    async def _handle_unhandled_exception(
        self, request: Request, exc: Exception
    ) -> StarletteResponse:
        """Handle unexpected exceptions."""
        from jinja2.exceptions import TemplateError as JinjaTemplateError

        # Check for a generic Exception handler
        handler = self._exception_handlers.get(Exception)
        if handler:
            result = handler(request, exc)
            if inspect.isawaitable(result):
                result = await result
            return result

        # Special handling for Template errors in debug mode
        if self.debug and isinstance(exc, JinjaTemplateError):
            return self._render_enhanced_template_error(request, exc)

        detail = str(exc) if self.debug else "Internal server error."
        traceback_text = None
        if self.debug:
            import traceback
            traceback_text = traceback.format_exc()
        return self._error_response(
            request=request, detail=detail, status_code=500,
            traceback_text=traceback_text,
        )

    def _render_enhanced_template_error(self, request: Request, exc: Exception) -> StarletteResponse:
        """Render a high-fidelity debug page for template errors."""
        import difflib
        import html as html_mod

        from jinja2.exceptions import TemplateSyntaxError, UndefinedError
        from starlette.responses import HTMLResponse

        status_code = 500
        title = "Template Error"
        name = getattr(exc, "name", "Unknown Template")
        lineno = getattr(exc, "lineno", 0)
        
        # Extract message - try multiple approaches
        message = str(exc) if exc else ""
        if not message or message.strip() == "":
            # Try accessing the message attribute directly
            message = getattr(exc, "message", None)
        if not message or message.strip() == "":
            # Try accessing msg attribute (some Jinja2 exceptions use this)
            message = getattr(exc, "msg", None)
        if not message or message.strip() == "":
            # Fallback to exception class name
            message = f"{type(exc).__name__}: An error occurred in the template"
        
        # Initialize diagnostic context early
        found_context = {}
        from jinja2.exceptions import TemplateSyntaxError, UndefinedError
        import difflib

        # Determine specific error type for badge
        badge = "Template Error"
        if isinstance(exc, TemplateSyntaxError):
            badge = "Syntax Error"
        elif isinstance(exc, UndefinedError):
            badge = "Undefined Variable"

        # Fuzzy suggestions for UndefinedError
        if isinstance(exc, UndefinedError):
            import re
            match = re.search(r"'([^']+)' is undefined", message)
            if match:
                missing_var = match.group(1)
                # We'll re-check found_context later if we find it in the stack
                # For now, just prep common globals
                candidates = ["request", "user", "url_for", "static"]
                matches = difflib.get_close_matches(missing_var, candidates, n=3, cutoff=0.6)
                if matches:
                    message += f" (Did you mean: {', '.join(matches)}?)"

        # Try to read the original template
        code_frame = ""

        # Find the template file
        search_dirs = [self.template_dir] if isinstance(self.template_dir, str) else (self.template_dir or [])
        template_path = None
        if name and name != "Unknown Template":
            for d in search_dirs:
                if not d: continue
                p = os.path.join(d, name)
                if os.path.exists(p):
                    template_path = p
                    break

        if template_path:
            try:
                with open(template_path, encoding="utf-8") as f:
                    source_lines = f.readlines()

                    if lineno > 0 and lineno <= len(source_lines):
                        start = max(0, lineno - 6)
                        end = min(len(source_lines), lineno + 5)

                        # Generate code frame with line numbers
                        frame_lines = []
                        for i in range(start, end):
                            curr_lineno = i + 1
                            is_error = curr_lineno == lineno
                            line_content = source_lines[i].rstrip()
                            prefix = " > " if is_error else "   "
                            frame_lines.append(f"{curr_lineno:4}{prefix}{line_content}")

                        code_frame = "\n".join(frame_lines)

                        # Apply Pygments if available
                        try:
                            from pygments import highlight
                            from pygments.formatters import HtmlFormatter
                            from pygments.lexers import get_lexer_for_filename

                            lexer = get_lexer_for_filename(template_path)
                            formatter = HtmlFormatter(style="monokai", nowrap=True)

                            highlighted_lines = []
                            for i in range(start, end):
                                curr_lineno = i + 1
                                is_error = curr_lineno == lineno
                                raw_line = source_lines[i]
                                html_line = highlight(raw_line, lexer, formatter)
                                klass = "error-line" if is_error else "normal-line"
                                highlighted_lines.append(
                                    f'<div class="{klass}"><span class="line-no">{curr_lineno:4}</span>{html_line}</div>'
                                )
                            code_frame = "".join(highlighted_lines)
                        except Exception:
                            # Fallback to escaped text if Pygments fails
                            code_frame = f"<pre><code>{html_mod.escape(code_frame)}</code></pre>"
            except Exception as read_exc:
                code_frame = f"<p class='text-red-500'>Could not read template source: {read_exc}</p>"

        # Extract context if available (Jinja2 internal context)
        import inspect
        try:
            for frame_info in inspect.trace():
                if "context" in frame_info.frame.f_locals:
                    ctx = frame_info.frame.f_locals["context"]
                    if hasattr(ctx, "get_all"):
                        found_context = ctx.get_all()
                        break
        except Exception:
            pass

        # Filter out noisy internal globals
        context_vars = {k: v for k, v in found_context.items()
                       if not k.startswith("__") and k not in ("range", "dict", "request")}


        # Render the premium debug page
        return self._render_premium_debug_page(
            title=title,
            message=message,
            filename=name,
            lineno=lineno,
            code_frame=code_frame,
            context_vars=context_vars,
            is_htmx=getattr(request, "headers", {}).get("HX-Request") == "true",
            badge=badge
        )

    def _render_premium_debug_page(
        self,
        title: str,
        message: str,
        filename: str,
        lineno: int,
        code_frame: str,
        context_vars: dict,
        is_htmx: bool,
        badge: str
    ) -> HTMLResponse:
        """Renders the high-fidelity Eden debug/error page with template variables."""
        from starlette.responses import HTMLResponse
        import html as html_mod
        import platform
        import sys

        Jakarta_Sans = "https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap"
        Outfit = "https://fonts.googleapis.com/css2?family=Outfit:wght@500;600;700&display=swap"
        
        # Get system info
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        os_name = platform.system()
        
        # Determine if we have Pygments code or raw pre
        is_raw = code_frame.strip().startswith("<pre>")
        
        # Format context variables for display
        def format_value(value, max_length=150):
            """Format a value safely for display."""
            try:
                if value is None:
                    return '<span class="text-slate-500 italic">None</span>'
                elif isinstance(value, bool):
                    return f'<span class="text-blue-400 font-mono">{str(value)}</span>'
                elif isinstance(value, (int, float)):
                    return f'<span class="text-emerald-400 font-mono">{value}</span>'
                elif isinstance(value, str):
                    escaped = html_mod.escape(value[:max_length])
                    if len(value) > max_length:
                        escaped += '...'
                    return f'<span class="text-amber-300 font-mono">"{escaped}"</span>'
                elif isinstance(value, dict):
                    return f'<span class="text-slate-400 font-mono">dict({len(value)} items)</span>'
                elif isinstance(value, (list, tuple)):
                    return f'<span class="text-slate-400 font-mono">{type(value).__name__}({len(value)} items)</span>'
                else:
                    type_name = type(value).__name__
                    return f'<span class="text-slate-400 font-mono">&lt;{type_name}&gt;</span>'
            except Exception:
                return '<span class="text-red-400">Unable to format</span>'
        
        # Escape message for safe display
        safe_message = html_mod.escape(message) if message else "An error occurred in the template"
        
        # Build variables table HTML
        variables_html = ""
        if context_vars:
            var_rows = []
            for key, value in sorted(context_vars.items())[:20]:  # Limit to 20
                safe_key = html_mod.escape(str(key))
                formatted_value = format_value(value)
                var_rows.append(f'<tr><td class="px-4 py-3 border-b border-slate-700/30"><code class="text-emerald-400 text-xs font-mono">{safe_key}</code></td><td class="px-4 py-3 border-b border-slate-700/30">{formatted_value}</td></tr>')
            
            remaining = len(context_vars) - 20
            if remaining > 0:
                var_rows.append(f'<tr><td colspan="2" class="px-4 py-3 text-center text-slate-500 italic text-xs">... and {remaining} more variables</td></tr>')
            
            variables_html = f'''<div class="p-8 space-y-6 border-t border-white/5">
                <div class="flex items-center justify-between">
                    <h3 class="text-xs font-bold text-slate-500 uppercase tracking-widest flex items-center gap-2">
                        <span class="w-1.5 h-1.5 rounded-full bg-emerald-600"></span>
                        Template Variables ({len(context_vars)})
                    </h3>
                </div>
                <div class="rounded-2xl overflow-hidden bg-slate-900/50 border border-white/5 shadow-inner">
                    <table class="w-full text-xs">
                        <thead><tr class="bg-slate-800/40 border-b border-white/5">
                            <th class="px-4 py-3 text-left text-slate-400 font-semibold">Variable</th>
                            <th class="px-4 py-3 text-left text-slate-400 font-semibold">Value</th>
                        </tr></thead>
                        <tbody>{''.join(var_rows)}</tbody>
                    </table>
                </div>
            </div>'''

        template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Eden - {title}</title>
    <link href="{Jakarta_Sans}" rel="stylesheet">
    <link href="{Outfit}" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        :root {{
            --bg-slate-900: #0f172a;
            --bg-slate-800: #1e293b;
            --accent-blue: #2563eb;
        }}
        body {{ 
            font-family: 'Plus Jakarta Sans', sans-serif; 
            background-color: var(--bg-slate-900);
            color: #f8fafc;
            margin: 0;
            line-height: 1.5;
        }}
        .premium-card {{
            background: rgba(30, 41, 59, 0.7);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        }}
        .error-badge {{
            background: rgba(239, 68, 68, 0.15);
            color: #fca5a5;
            border: 1px solid rgba(239, 68, 68, 0.3);
            font-family: 'Outfit', sans-serif;
            letter-spacing: 0.05em;
        }}
        .highlight {{ background: transparent !important; }}
        pre {{ margin: 0; padding: 1.5rem; overflow-x: auto; background: rgba(15, 23, 42, 0.5) !important; border-radius: 0.75rem; }}
        code {{ font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 0.9em; }}
        .line-no {{ color: #475569; padding-right: 1.5rem; user-select: none; display: inline-block; width: 3rem; text-align: right; }}
        .error-line {{ background: rgba(239, 68, 68, 0.15) !important; display: block; width: 100%; border-left: 3px solid #ef4444; }}
        .normal-line {{ display: block; width: 100%; border-left: 3px solid transparent; }}
        
        /* Custom scrollbar */
        ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
        ::-webkit-scrollbar-track {{ background: rgba(15, 23, 42, 0.1); }}
        ::-webkit-scrollbar-thumb {{ background: rgba(255, 255, 255, 0.1); border-radius: 4px; }}
        ::-webkit-scrollbar-thumb:hover {{ background: rgba(255, 255, 255, 0.2); }}

        @keyframes slideUp {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        .animate-slide-up {{ animation: slideUp 0.6s cubic-bezier(0.16, 1, 0.3, 1); }}
    </style>
</head>
<body class="min-h-screen py-16 px-4 selection:bg-blue-500/30">
    <div class="max-w-5xl mx-auto space-y-10 animate-slide-up">
        
        <!-- Header Section -->
        <div class="space-y-4">
            <div class="flex items-center gap-3">
                <span class="px-3 py-1 text-[10px] font-black uppercase rounded-full error-badge tracking-[0.2em]">
                    {badge}
                </span>
            </div>
            <h1 class="text-5xl font-black tracking-tighter text-white font-['Outfit']">
                {title}
            </h1>
            <div class="flex items-center gap-2 text-slate-400 font-medium bg-slate-800/30 w-fit px-3 py-1.5 rounded-lg border border-white/5">
                <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <span class="text-xs font-mono">{filename or "inline template"}</span>
                <span class="text-slate-600">•</span>
                <span class="text-xs">Line {lineno}</span>
            </div>
        </div>

        <!-- Main Content Area -->
        <div class="premium-card rounded-3xl overflow-hidden">
            <!-- Error Banner -->
            <div class="bg-red-500/10 border-b border-white/5 p-8">
                <div class="text-slate-100 text-lg font-medium leading-relaxed">
                    {safe_message}
                </div>
            </div>

            <!-- Code Explorer -->
            <div class="p-8 space-y-6">
                <div class="flex items-center justify-between">
                    <h3 class="text-xs font-bold text-slate-500 uppercase tracking-widest flex items-center gap-2">
                        <span class="w-1.5 h-1.5 rounded-full bg-slate-600"></span>
                        Code Explorer
                    </h3>
                </div>
                
                <div class="rounded-2xl overflow-hidden bg-slate-900/50 border border-white/5 shadow-inner">
                    {code_frame if not is_raw else f'<div class="p-4">{code_frame}</div>'}
                </div>
            </div>

            {variables_html}

            <!-- Environment Footer within Card -->
            <div class="bg-slate-900/40 p-8 border-t border-white/5">
                 <h3 class="text-xs font-bold text-slate-500 uppercase tracking-widest mb-6 flex items-center gap-2">
                    <span class="w-1.5 h-1.5 rounded-full bg-slate-600"></span>
                    Environment Snapshot
                </h3>
                <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div class="bg-slate-800/40 p-4 rounded-2xl border border-white/5">
                        <p class="text-[10px] uppercase font-bold text-slate-500 mb-1">OS</p>
                        <p class="text-slate-200 font-semibold text-xs">{os_name}</p>
                    </div>
                    <div class="bg-slate-800/40 p-4 rounded-2xl border border-white/5">
                        <p class="text-[10px] uppercase font-bold text-slate-500 mb-1">Python</p>
                        <p class="text-slate-200 font-semibold text-xs">{python_version}</p>
                    </div>
                    <div class="bg-slate-800/40 p-4 rounded-2xl border border-white/5">
                        <p class="text-[10px] uppercase font-bold text-slate-500 mb-1">Eden</p>
                        <p class="text-slate-200 font-semibold text-xs">v0.1.0</p>
                    </div>
                    <div class="bg-slate-800/40 p-4 rounded-2xl border border-white/5">
                        <p class="text-[10px] uppercase font-bold text-slate-500 mb-1">Status</p>
                        <div class="flex items-center gap-2">
                            <span class="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_#10b981]"></span>
                            <span class="text-emerald-400 font-bold text-xs uppercase italic">Debug On</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Feedback Footer -->
        <div class="flex justify-center pt-4">
            <p class="text-slate-600 text-[10px] font-medium uppercase tracking-[0.3em]">
                Eden Framework • Premium Debug Engine
            </p>
        </div>
    </div>
</body>
</html>
"""
        return HTMLResponse(content=template, status_code=500)

    async def _handle_starlette_http_exception(
        self, request: Request, exc: StarletteHTTPException
    ) -> StarletteResponse:
        """Handle Starlette-level HTTP errors (404, 405) to return styled pages or JSON."""
        return self._error_response(
            request=request,
            detail=exc.detail or "Not found",
            status_code=exc.status_code,
        )

    async def _handle_no_match_found(
        self, request: Request, exc: Exception
    ) -> StarletteResponse:
        """Handle Starlette routing exceptions (e.g., NoMatchFound from url_for)."""
        # Extract a friendly message from the exception
        exc_str = str(exc)
        if "No route exists" in exc_str:
            detail = "The requested route or URL name does not exist."
        else:
            detail = exc_str if self.debug else "Route not found."
        
        return self._error_response(
            request=request,
            detail=detail,
            status_code=404,
        )

    @staticmethod
    def _is_html_request(request: Any) -> bool:
        """Check if the client prefers HTML (browser) over JSON (API)."""
        try:
            accept = ""
            if hasattr(request, "headers"):
                accept = request.headers.get("accept", "")
            return "text/html" in accept
        except Exception:
            return False

    def _error_response(
        self,
        detail: str,
        status_code: int,
        extra: dict[str, Any] | None = None,
        request: Any = None,
        traceback_text: str | None = None,
    ) -> StarletteResponse:
        """Unified error response — styled HTML for browsers, JSON for APIs."""
        from starlette.responses import HTMLResponse

        # If the client accepts HTML, render a styled error page
        if request and self._is_html_request(request):
            return HTMLResponse(
                content=self._render_error_page(status_code, detail, traceback_text),
                status_code=status_code,
            )

        # Default: JSON response for API clients
        content = {
            "error": True,
            "status_code": status_code,
            "detail": detail,
        }
        if extra:
            content["extra"] = extra
        return JsonResponse(content=content, status_code=status_code)

    @staticmethod
    def _render_error_page(
        status_code: int, detail: str, traceback_text: str | None = None
    ) -> str:
        """Render a styled HTML error page matching Eden's dark theme."""
        import html as html_mod

        STATUS_MESSAGES = {
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Page Not Found",
            405: "Method Not Allowed",
            408: "Request Timeout",
            409: "Conflict",
            422: "Unprocessable Entity",
            429: "Too Many Requests",
            500: "Internal Server Error",
            502: "Bad Gateway",
            503: "Service Unavailable",
        }

        STATUS_ICONS = {
            400: "⚠️", 401: "🔒", 403: "🚫", 404: "🔍",
            405: "🚧", 422: "📋", 429: "🐢", 500: "💥",
            502: "🔌", 503: "🛠️",
        }

        title = STATUS_MESSAGES.get(status_code, "Error")
        icon = STATUS_ICONS.get(status_code, "❌")
        safe_detail = html_mod.escape(detail)

        traceback_html = ""
        if traceback_text:
            safe_tb = html_mod.escape(traceback_text)
            traceback_html = f"""
            <details class="traceback">
                <summary>Stack Trace (debug mode)</summary>
                <pre>{safe_tb}</pre>
            </details>
            """

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{status_code} — {title}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
            background: #0F172A;
            color: #e2e8f0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 24px;
        }}
        .error-container {{
            text-align: center;
            max-width: 520px;
            width: 100%;
        }}
        .error-icon {{
            font-size: 4rem;
            margin-bottom: 16px;
            filter: drop-shadow(0 0 24px rgba(37, 99, 235, 0.3));
            animation: float 3s ease-in-out infinite;
        }}
        @keyframes float {{
            0%, 100% {{ transform: translateY(0); }}
            50% {{ transform: translateY(-8px); }}
        }}
        .error-code {{
            font-size: 6rem;
            font-weight: 800;
            letter-spacing: -2px;
            background: linear-gradient(135deg, #2563EB, #7c3aed);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            line-height: 1;
            margin-bottom: 8px;
        }}
        .error-title {{
            font-size: 1.4rem;
            font-weight: 600;
            color: #f1f5f9;
            margin-bottom: 12px;
        }}
        .error-detail {{
            font-size: 0.95rem;
            color: #94a3b8;
            line-height: 1.6;
            margin-bottom: 28px;
            padding: 0 12px;
        }}
        .btn-home {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 12px 28px;
            background: #2563EB;
            color: #fff;
            border: none;
            border-radius: 10px;
            font-size: 0.9rem;
            font-weight: 600;
            text-decoration: none;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
        }}
        .btn-home:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(37, 99, 235, 0.4);
        }}
        .btn-secondary {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 12px 28px;
            background: transparent;
            color: #94a3b8;
            border: 1px solid #334155;
            border-radius: 10px;
            font-size: 0.9rem;
            font-weight: 500;
            text-decoration: none;
            cursor: pointer;
            margin-left: 10px;
            transition: all 0.3s ease;
        }}
        .btn-secondary:hover {{
            border-color: #475569;
            color: #e2e8f0;
        }}
        .actions {{ margin-bottom: 32px; }}
        .brand {{
            font-size: 0.78rem;
            color: #475569;
            letter-spacing: 0.5px;
        }}
        .brand span {{ color: #2563EB; }}
        .traceback {{
            text-align: left;
            margin-top: 28px;
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 10px;
            padding: 4px;
            max-width: 100%;
        }}
        .traceback summary {{
            padding: 10px 14px;
            cursor: pointer;
            font-size: 0.82rem;
            color: #f59e0b;
            font-weight: 500;
            user-select: none;
        }}
        .traceback pre {{
            padding: 12px 14px;
            font-size: 0.75rem;
            line-height: 1.5;
            color: #94a3b8;
            overflow-x: auto;
            white-space: pre-wrap;
            word-break: break-word;
            max-height: 320px;
            overflow-y: auto;
        }}
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-icon">{icon}</div>
        <div class="error-code">{status_code}</div>
        <div class="error-title">{title}</div>
        <div class="error-detail">{safe_detail}</div>
        <div class="actions">
            <a href="/" class="btn-home">← Go Home</a>
            <a href="javascript:history.back()" class="btn-secondary">Go Back</a>
        </div>
        {traceback_html}
        <div class="brand">Powered by <span>Eden 🌿</span></div>
    </div>
</body>
</html>"""

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI entry point."""
        scope["eden_app"] = self
        app = await self.build()
        await app(scope, receive, send)

    # ── Dev Server ───────────────────────────────────────────────────────

    def run(
        self,
        host: str = "127.0.0.1",
        port: int = 8000,
        reload: bool = True,
        workers: int = 1,
        log_level: str = "info",
    ) -> None:
        """
        Start the development server via Uvicorn.

        Args:
            host: Bind address.
            port: Bind port.
            reload: Enable auto-reload on code changes.
            workers: Number of worker processes.
            log_level: Logging level.
        """
        from eden.port import find_available_port

        resolved_port = find_available_port(host, port)
        if resolved_port != port:
            print(f"\n  ⚠️  Port {port} in use → using {resolved_port}")

        print(f"\n  🌿 Eden v{self.version}")
        print(f"  📡 Running on http://{host}:{resolved_port}")
        print(f"  🔄 Auto-reload: {'enabled' if reload else 'disabled'}\n")

        uvicorn.run(
            self,
            host=host,
            port=resolved_port,
            reload=reload,
            workers=workers,
            log_level=log_level,
        )
