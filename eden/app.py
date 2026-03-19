"""
Eden — Application

The main `Eden` class: your entry point for building an ASGI web application.
Combines routing, middleware, dependency injection, exception handling,
and lifespan management into a clean, decorator-driven API.
"""

from __future__ import annotations

import inspect
import os
import re
import asyncio
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, Dict, Optional, Type, Union

from starlette.applications import Starlette
from starlette.datastructures import State
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware import Middleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse, HTMLResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

import uvicorn

if TYPE_CHECKING:
    from eden.cache import CacheBackend

from eden.exceptions import EdenException
from eden.middleware import get_middleware_class
from eden.requests import Request
from eden.responses import HtmlResponse, JsonResponse
from eden.routing import Router
from eden.storage import LocalStorageBackend
from eden.storage import storage as eden_storage
from eden.tasks import EdenBroker, create_broker
from eden.templating import EdenTemplates
from eden.core.backends.redis import RedisBackend
from eden.core.metrics import metrics
from eden.core.idempotency import IdempotencyManager
from eden.websocket.manager import connection_manager

if TYPE_CHECKING:
    from eden.storage import StorageManager
    from eden.config import Config


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

    # Default priorities for middleware ordering
    # Lower values run FIRST (outermost) in the request cycle,
    # then inner logic runs, then LAST in the response cycle.
    PRIORITY_LOW = 1000
    PRIORITY_STANDARD = 500
    PRIORITY_HIGH = 100
    PRIORITY_CORE = 0

    def __init__(
        self,
        title: str | None = None,
        version: str | None = None,
        debug: bool = False,
        description: str | None = None,
        secret_key: str | None = None,
        config: dict[str, Any] | Config | None = None,
        static_dir: str = "static",
        static_url: str = "/static",
        templates_dir: str = "templates",
        browser_reload: bool = True,
    ) -> None:
        from eden.context import set_app
        set_app(self)

        # Precedence: Explicit constructor arguments > config object values
        # Load configuration if not provided
        from eden.config import Config, get_config
        if config is None:
            self.config = get_config()
        elif isinstance(config, dict):
            self.config = Config(**config)
        else:
            self.config = config
        
        # Configure with explicit overrides
        self.title = title or self.config.title or "Eden App"
        self.version = version or self.config.version or "0.1.0"
        self.description = description or getattr(self.config, "description", None)
        self.secret_key = secret_key or self.config.secret_key or "eden-insecure-secret-key"
        
        # debug is special as it's a bool
        # Priority: Explicit True > Config > Default False
        self.debug = debug or self.config.debug or False
        
        # Apply config to state for bootstrappers and other components
        self.state = State()
        self._apply_config()
        
        self.browser_reload = self.config.browser_reload
        self.template_dir = "templates"
        self.media_dir = "media"
        self.static_dir = "static"
        self.static_url = "/static"

        self._router = Router()
        self._middleware_stack: list[tuple[type, dict[str, Any], int]] = []
        self._exception_handlers: dict[type[Exception] | int, Callable] = {}
        self._defaults_setup_done = False
        
        from eden.exceptions.dispatcher import ExceptionDispatcher
        self._exception_dispatcher = ExceptionDispatcher(self)
        
        self.mount_paths: dict[str, str] = {}
        self._startup_handlers: list[Callable] = []
        self._shutdown_handlers: list[Callable] = []

        # Task Queue with safety fallback
        try:
            # In test mode, we default to InMemoryBroker unless redis_url is explicitly set
            is_test = self.is_test()
            
            redis_url = None
            if not is_test:
                redis_url = self.config.redis_url
                
            self._raw_broker = create_broker(redis_url)
        except Exception as e:
            from eden.logging import get_logger
            get_logger("eden").warning(f"Failed to create broker: {e}. Falling back to InMemoryBroker.")
            self._raw_broker = create_broker(None)
            redis_url = None
            
        self._eden_broker = EdenBroker(self._raw_broker)
        self._eden_broker.app = self
        self.broker = self._eden_broker
        
        # Distributed Backend (Locking / PubSub)
        self.distributed_backend = None
        self.metrics = metrics
        self.idempotency: Optional[IdempotencyManager] = None
        
        if redis_url:
            try:
                self.distributed_backend = RedisBackend(url=redis_url)
                self.metrics.set_distributed_backend(self.distributed_backend)
                self.idempotency = IdempotencyManager(self.distributed_backend)
                self.broker.set_distributed_backend(self.distributed_backend)
                # We'll initialize the connection_manager in build() or lifespan
            except Exception as e:
                from eden.logging import get_logger
                get_logger("eden").warning(f"Failed to initialize distributed backend: {e}")
        
        # Templating
        self._templates: EdenTemplates | None = None
        
        # Storage
        self.storage: "StorageManager" = eden_storage
        self.storage.register(
            "local",
            LocalStorageBackend(base_path=self.media_dir, base_url="/media/"),
            default=True
        )

        # Built ASGI app (lazy)
        self._app: Starlette | None = None
        self._build_lock = asyncio.Lock()

        # Health checks
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
        
        self.setup_defaults()

    def _apply_config(self) -> None:
        """Sync configuration values to internal attributes and app state."""
        # Sync core attributes - only if not already set by constructor
        if not getattr(self, "title", None):
            self.title = getattr(self.config, "title", "Eden App")
        if not getattr(self, "version", None):
            self.version = getattr(self.config, "version", "0.1.0")
        if self.debug is None:
            self.debug = getattr(self.config, "debug", False)
        if not getattr(self, "secret_key", None):
            self.secret_key = getattr(self.config, "secret_key", None)

        # Sync key URLs and settings to state for bootstrappers
        self.state.database_url = getattr(self.config, "database_url", None)
        self.state.redis_url = getattr(self.config, "redis_url", None)
        self.state.env = getattr(self.config, "env", "dev")
        self.state.debug = self.debug

        # Populate extra config into state for general access
        if hasattr(self.config, "model_dump"):
            config_dict = self.config.model_dump()
            for key, value in config_dict.items():
                if not hasattr(self.state, key):
                    setattr(self.state, key, value)

    def setup_tasks(self) -> None:
        """Hook for initializing/configuring task lifecycle and dependencies."""
        pass

    @classmethod
    def get_current(cls) -> Eden:
        """Get the current active Eden application instance."""
        from eden.context import get_app
        app = get_app()
        # If the app in context is the Starlette instance, unwrap it to get Eden
        if app and hasattr(app, "eden"):
            return app.eden
        return app

    # ── Health Checks ─────────────────────────────────────────────────────

    def enable_health_checks(
        self,
        health_path: str = "/health",
        ready_path: str = "/ready",
    ) -> None:
        """
        Register /health and /ready endpoints with deep infrastructure probes.
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
            
            # 1. Built-in infrastructure probes
            probes = {}
            all_ok = True
            
            # Redis / Distributed Backend check
            if self.distributed_backend:
                try:
                    # Depending on backend implementation, this might be a ping()
                    # or just checking connection state.
                    if hasattr(self.distributed_backend, "ping"):
                        await self.distributed_backend.ping()
                    probes["distributed_backend"] = "ok"
                except Exception as e:
                    probes["distributed_backend"] = f"error: {str(e)}"
                    all_ok = False
            
            # Database check
            try:
                from eden.db import Model
                db = getattr(Model, "_db", None)
                if db:
                    async with db.engine.connect() as conn:
                        from sqlalchemy import text
                        await conn.execute(text("SELECT 1"))
                    probes["db:default"] = "ok"
            except Exception as e:
                probes["db:default"] = f"error: {str(e)}"
                all_ok = False

            # Media Storage check
            if self.storage:
                try:
                    # Check if at least one backend is registered and active
                    # This is a light probe to ensure the storage system is initialized
                    if not self.storage._backends:
                        probes["storage"] = "error: no backends registered"
                        all_ok = False
                    else:
                        probes["storage"] = "ok"
                except Exception as e:
                    probes["storage"] = f"error: {str(e)}"
                    all_ok = False

            # 2. User-registered checks
            checks = self._health_checks.copy()
            results: dict[str, Any] = {}
            for name, check_fn in checks:
                try:
                    if asyncio.iscoroutinefunction(check_fn):
                        result = await check_fn()
                    else:
                        result = check_fn()
                    results[name] = result or "ok"
                except Exception as e:
                    results[name] = f"failed: {str(e)}"
                    all_ok = False
            
            # Update overall health metric
            status_val = 1 if all_ok else 0
            self.metrics.set_gauge("app_health_status", status_val)

            return {
                "status": "ready" if all_ok else "unready",
                "probes": probes,
                "custom_checks": results
            }

    def add_readiness_check(self, name: str, check_fn: Callable | None = None) -> Callable | None:
        """Register a readiness check function."""
        if check_fn is None:
            def decorator(func: Callable) -> Callable:
                self._health_checks.append((name, func))
                return func
            return decorator
            
        self._health_checks.append((name, check_fn))

    # ── Route Decorators ─────────────────────────────────────────────────
    
    def validate(self, schema: Type[Any], template: str | None = None) -> Callable:
        """Decorator for automatic form validation."""
        import functools
        from eden.forms import BaseForm, Schema

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
                            data = dict(await request.form())
                        except (ValueError, RuntimeError):
                            pass
                    form = BaseForm(schema=schema, data=data)

                # 2. Validate
                if form.is_valid():
                    sig = inspect.signature(func)
                    # Inject model instance
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
                    if hasattr(request, "session"):
                        request.session["_old_input"] = form.data
                    return self.render(template, form=form)
                
                return JsonResponse({"errors": form.errors}, status_code=400)

            return wrapper
        return decorator

    def route(self, path: str, **kwargs) -> Callable:
        return self._router.route(path, **kwargs)

    def get(self, path: str, **kwargs) -> Callable:
        return self._router.get(path, **kwargs)

    def post(self, path: str, **kwargs) -> Callable:
        return self._router.post(path, **kwargs)

    def put(self, path: str, **kwargs) -> Callable:
        return self._router.put(path, **kwargs)

    def patch(self, path: str, **kwargs) -> Callable:
        return self._router.patch(path, **kwargs)

    def delete(self, path: str, **kwargs) -> Callable:
        return self._router.delete(path, **kwargs)

    def options(self, path: str, **kwargs) -> Callable:
        return self._router.options(path, **kwargs)

    def head(self, path: str, **kwargs) -> Callable:
        return self._router.head(path, **kwargs)

    def websocket(self, path: str, **kwargs) -> Callable:
        return self._router.websocket(path, **kwargs)

    # ── Templating ───────────────────────────────────────────────────────

    @property
    def templates(self) -> EdenTemplates:
        """Access the templating engine."""
        if self._templates is None:
            directories = [self.template_dir]
            import eden.auth
            auth_templates = os.path.join(os.path.dirname(eden.auth.__file__ or ""), "templates")
            if os.path.isdir(auth_templates):
                directories.append(auth_templates)
            self._templates = EdenTemplates(directory=directories)
        return self._templates

    def render(self, template_name: str, context: dict[str, Any] | None = None, **kwargs: Any) -> Any:
        ctx = context or {}
        ctx.update(kwargs)
        if "request" not in ctx:
            try:
                from eden.context import get_request
                ctx["request"] = get_request()
            except Exception:
                pass
        return self.templates.TemplateResponse(template_name, ctx)

    # ── Sub-Router ───────────────────────────────────────────────────────

    def include_router(self, router: Router, prefix: str = "") -> None:
        from eden.websocket.router import WebSocketRouter
        if isinstance(router, WebSocketRouter):
            router.mount(self)
            return
        self._router.include_router(router, prefix=prefix)

    def add_view(self, path: str, view_class: type, **kwargs: Any) -> None:
        self._router.add_view(path, view_class, **kwargs)

    def url_for(self, name: str, **path_params: Any) -> str:
        return self._router.url_for(name, **path_params)

    def get_routes(self) -> list[dict[str, Any]]:
        routes_info = []
        for route in self._router.routes:
            from eden.routing import WebSocketRoute
            is_ws = isinstance(route, WebSocketRoute)
            routes_info.append({
                "path": route.path,
                "name": route.name,
                "type": "websocket" if is_ws else "http",
                "methods": [] if is_ws else getattr(route, "methods", ["GET"]),
            })
        return routes_info

    # ── SaaS Features ────────────────────────────────────────────────────

    def mount_admin(self, path: str = "/admin", admin_site=None) -> None:
        from eden.admin import admin as default_admin
        site = admin_site or default_admin
        router = site.build_router(prefix=path)
        self.include_router(router)

    def configure_mail(self, backend) -> None:
        from eden.mail import configure_mail as _configure_mail
        self.mail = backend
        _configure_mail(backend)

    @property
    def task(self) -> EdenBroker:
        return self._eden_broker

    # ── Middleware ───────────────────────────────────────────────────────

    def add_middleware(self, middleware: str | type, priority: int = PRIORITY_STANDARD, **kwargs: Any) -> None:
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

        # If custom CORS is added, remove the default (empty) CORSMiddleware entry
        try:
            from eden.middleware import CORSMiddleware
            if isinstance(cls, type) and issubclass(cls, CORSMiddleware):
                self._middleware_stack = [
                    m for m in self._middleware_stack
                    if not (isinstance(m[0], type) and issubclass(m[0], CORSMiddleware))
                ]
        except Exception:
            pass

        self._middleware_stack.append((cls, kwargs, priority))

    def is_test(self) -> bool:
        """Determines if the application is running in a test environment."""
        import sys
        # Explicit env var takes precedence
        env = os.getenv("EDEN_ENV", "").lower()
        if env == "test" or env == "testing":
            return True
        if env in ("production", "prod", "development", "dev"):
            return False

        return (
            getattr(self.config, "env", "") == "test" or
            (hasattr(self.config, "is_test") and self.config.is_test() if callable(getattr(self.config, "is_test", None)) else getattr(self.config, "is_test", False)) or
            "pytest" in sys.modules
        )

    def setup_defaults(self) -> None:
        """Register recommended default middleware in correct execution order."""
        if self._defaults_setup_done:
            return

        # 1. Traceability & Context (Outermost)
        self.add_middleware("request_id", priority=self.PRIORITY_CORE - 10)
        
        # 2. Security & Session Protection
        self.add_middleware("security", priority=self.PRIORITY_CORE + 10)
        
        # 3. Session & CSRF (Conditional chain)
        # We disable these by default in tests to simplify TestClient usage
        if self.secret_key and not self.is_test():
            self.add_middleware("session", priority=self.PRIORITY_CORE + 20, secret_key=self.secret_key)
            self.add_middleware("csrf", priority=self.PRIORITY_CORE + 30)
            self.add_middleware("messages", priority=self.PRIORITY_CORE + 40)
        elif self.debug and not self.is_test():
            from eden.logging import get_logger
            get_logger("eden").warning("secret_key not set. Session, CSRF, and Messages middleware disabled.")
        
        # 4. Standard App Middleware
        auth_backends = None
        if self.secret_key:
            from eden.auth.backends.session import SessionBackend
            from eden.auth.backends.jwt import JWTBackend
            auth_backends = [SessionBackend(), JWTBackend(secret_key=self.secret_key)]
        
        self.add_middleware("auth", priority=self.PRIORITY_HIGH, backends=auth_backends)
        self.add_middleware("gzip", priority=self.PRIORITY_LOW)
        
        # 5. CORS (Secure by default: block all unless configured)
        # Check for existing custom CORS before adding default
        from eden.middleware import CORSMiddleware as _BaseCORSMiddleware

        has_cors = any(
            (isinstance(m[0], type) and issubclass(m[0], _BaseCORSMiddleware)) or
            (isinstance(m[0], str) and m[0] == "cors")
            for m in self._middleware_stack
        )
        if not has_cors:
            self.add_middleware("cors", priority=self.PRIORITY_STANDARD, allow_origins=[])
        self._defaults_setup_done = True
    # ── Lifespan Hooks ───────────────────────────────────────────────────

    def on_startup(self, func: Callable) -> Callable:
        self._startup_handlers.append(func)
        return func

    def on_shutdown(self, func: Callable) -> Callable:
        self._shutdown_handlers.append(func)
        return func

    # ── Exception Handlers ───────────────────────────────────────────────

    def exception_handler(self, exc_class: type[Exception] | int) -> Callable:
        def decorator(func: Callable) -> Callable:
            self._exception_handlers[exc_class] = func
            return func
        return decorator

    def register_error_handler(self, handler: Any) -> None:
        """
        Register a custom ErrorHandler instance.
        """
        from eden.exceptions import ErrorHandler, error_handler_registry
        if not isinstance(handler, ErrorHandler):
            raise ValueError(f"Expected ErrorHandler instance, got {type(handler)}")
        error_handler_registry.register(handler)

    def register_exception_handler(self, exc_class: type[Exception] | int, handler: Callable) -> None:
        """
        Programmatically register an exception handler.
        """
        self._exception_handlers[exc_class] = handler

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI interface for the application."""
        if self._app is None:
            await self.build()
        
        # At this point self._app is definitely not None
        assert self._app is not None
        await self._app(scope, receive, send)

    def _build_websockets(self, routes: list) -> None:
        if self.debug and self.browser_reload:
            from starlette.routing import WebSocketRoute as StarletteWebSocketRoute
            from starlette.websockets import WebSocket

            async def reload_websocket(websocket: WebSocket) -> None:
                await websocket.accept()
                try:
                    while True:
                        await websocket.receive_text()
                except Exception:
                    pass
            routes.insert(0, StarletteWebSocketRoute("/_eden/reload", reload_websocket))

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
                pass
            finally:
                await manager.disconnect(websocket)
        routes.insert(0, StarletteWebSocketRoute("/_eden/sync", sync_websocket, name="eden:sync"))

    def _build_services(self) -> None:
        from eden.bootstrappers import ServiceBootstrapper
        ServiceBootstrapper.bootstrap_all(self)

    def _build_middleware(self) -> list[Middleware]:
        # Start with core internal middleware that MUST be outermost
        from eden.context_middleware import ContextMiddleware
        from eden.error_middleware import ErrorHandlerMiddleware
        
        # Build the final stack including user-added middleware
        # Lower priority = OUTERMOST in the onion (runs first on request, last on response)
        
        # Prepare explicit list with priorities for internal ones
        # Use low priority numbers for OUTER-MOST middleware
        final_stack = [
            (get_middleware_class("correlation"), {}, self.PRIORITY_CORE - 10),
            (ContextMiddleware, {}, self.PRIORITY_CORE),
            (get_middleware_class("request"), {}, self.PRIORITY_CORE + 1),
            (ErrorHandlerMiddleware, {}, self.PRIORITY_CORE + 2),
        ]
        
        # Add user stack
        final_stack.extend(self._middleware_stack)
        
        # Add browser reload if enabled (Should be inner-most to inject script last)
        if self.debug and self.browser_reload:
            # We use a lower priority number (inner-most) to ensure it runs LATER 
            # in the response cycle, effectively being the last thing to touch the body.
            final_stack.append((get_middleware_class("browser_reload"), {}, self.PRIORITY_LOW + 500))
            
        # Sort by priority
        final_stack.sort(key=lambda x: x[2])
        
        # Build Starlette Middleware objects
        return [
            Middleware(cls, **kwargs) for cls, kwargs, _ in final_stack
        ]

    def _build_exception_handlers(self) -> dict:
        exception_handlers = {
            exc_cls: self._wrap_exception_handler(handler)
            for exc_cls, handler in self._exception_handlers.items()
        }
        exception_handlers[Exception] = self._handle_exception
        exception_handlers[StarletteHTTPException] = self._handle_exception
        
        from jinja2.exceptions import TemplateError as JinjaTemplateError
        if JinjaTemplateError not in exception_handlers:
            exception_handlers[JinjaTemplateError] = self._render_enhanced_template_error

        from starlette.routing import NoMatchFound
        if NoMatchFound not in exception_handlers:
            exception_handlers[NoMatchFound] = self._handle_exception
        return exception_handlers

    async def build(self) -> Starlette:
        if self._app is not None:
            return self._app

        async with self._build_lock:
            if self._app is not None:
                return self._app

            self.setup_defaults()
            starlette_routes = self._router.to_starlette_routes()
            self._build_websockets(starlette_routes)
            
            from eden.components import get_component_router
            starlette_routes.extend(get_component_router().to_starlette_routes())

            self._build_services()
            self._configure_static_files(starlette_routes)
            
            self._app = Starlette(
                debug=self.debug,
                routes=starlette_routes,
                middleware=self._build_middleware(),
                exception_handlers=self._build_exception_handlers(),
                lifespan=self._configure_lifespan(),
            )
            # Use state for typed extension and attribute for legacy access
            self._app.state.eden = self
            setattr(self._app, "eden", self)
            
            # Proxy core methods to underlying Starlette app for consistency
            setattr(self._app, "render", self.render)
            setattr(self._app, "url_for", self.url_for)
            
            return self._app

    def _configure_lifespan(self) -> Callable:
        @asynccontextmanager
        async def lifespan(app: Starlette) -> AsyncGenerator[None, None]:
            if self.distributed_backend:
                await self.distributed_backend.connect()
                # Set distributed backend on connection manager
                from eden.websocket.manager import connection_manager
                await connection_manager.set_distributed_backend(self.distributed_backend)
                # Set config based on app settings
                connection_manager.allowed_origins = [re.compile(o) for o in (getattr(self.config, "allowed_origins", []) or [])]
                connection_manager.require_csrf = getattr(self.config, "require_websocket_csrf", False)
            
            # Set app on metrics
            self.metrics.set_gauge("app_info", 1, labels={"version": "1.0", "env": getattr(self.config, "env", "development")})
                
            await self.broker.startup()
            for handler in self._startup_handlers:
                result = handler()
                if inspect.isawaitable(result):
                    await result
            yield
            # Graceful shutdown order:
            # 1. Broadcasters/Broker
            await self.broker.shutdown()
            
            # 2. WebSocket cleanup (flush buffers, close handles)
            from eden.websocket.manager import connection_manager
            await connection_manager.shutdown()
            
            # 3. Backend disconnection
            if self.distributed_backend:
                await self.distributed_backend.disconnect()

            # 4. Custom shutdown handlers
            for handler in self._shutdown_handlers:
                result = handler()
                if inspect.isawaitable(result):
                    await result
        return lifespan

    def _configure_static_files(self, routes: list) -> None:
        """Mount static files route if directory exists, with caching for optimization."""
        if not hasattr(self, "_static_dir_exists"):
            self._static_dir_exists = os.path.isdir(self.static_dir)
            
        if self._static_dir_exists:
            from starlette.routing import Mount
            from starlette.staticfiles import StaticFiles
            routes.append(Mount(self.static_url, app=StaticFiles(directory=self.static_dir), name="static"))

    async def _handle_exception(self, request: Request, exc: Exception) -> StarletteResponse:
        from eden.exceptions import error_handler_registry
        return await error_handler_registry.handle_exception(exc, request, self)

    def _render_enhanced_template_error(self, request: Request, exc: Exception) -> StarletteResponse:
        from eden.exceptions.debug import render_enhanced_template_error
        return render_enhanced_template_error(self, request, exc)

    async def _error_response(self, request: Request, status_code: int, detail: str, traceback_text: str | None = None) -> StarletteResponse:
        return await self._exception_dispatcher._error_response(request, status_code, detail, traceback_text)

    def _wrap_exception_handler(self, handler: Callable) -> Callable:
        async def wrapped_handler(request: StarletteRequest, exc: Exception) -> StarletteResponse:
            eden_request = Request(request.scope, request.receive)
            result = handler(eden_request, exc)
            if inspect.isawaitable(result):
                return await result
            return result
        return wrapped_handler

    def run(self, host: str = "127.0.0.1", port: int = 8000, **kwargs: Any) -> None:
        if self.debug:
            os.environ["EDEN_DEBUG"] = "true"
        reload = kwargs.pop("reload", self.debug)
        uvicorn.run(self, host=host, port=port, reload=reload, lifespan="on", **kwargs)

def create_app(**kwargs: Any) -> Eden:
    """
    Factory function to create and configure an Eden application.
    Convenience helper for main.py and testing.
    
    Args:
        **kwargs: Arguments passed to the Eden constructor
        
    Returns:
        Configured Eden instance
    """
    return Eden(**kwargs)
