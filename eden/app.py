"""
Eden — Application

The main `Eden` class: your entry point for building an ASGI web application.
Combines routing, middleware, dependency injection, exception handling,
and lifespan management into a clean, decorator-driven API.
"""

from __future__ import annotations

import inspect
import os
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
        self._exception_handlers: dict[type[Exception] | int, Callable] = {}
        
        from eden.exceptions.dispatcher import ExceptionDispatcher
        self._exception_dispatcher = ExceptionDispatcher(self)
        
        self.mount_paths: dict[str, str] = {}
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

    def setup_tasks(self) -> None:
        """Hook for initializing/configuring task lifecycle and dependencies."""
        pass

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

    def add_middleware(self, middleware: str | type, **kwargs: Any) -> None:
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
        
        self._middleware_stack.append((cls, kwargs))

    def setup_defaults(self) -> None:
        self.add_middleware("security")
        self.add_middleware("session", secret_key=self.secret_key)
        self.add_middleware("csrf")
        self.add_middleware("auth")
        self.add_middleware("gzip")
        self.add_middleware("cors", allow_origins=["*"])

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

    # ── ASGI Interface ───────────────────────────────────────────────────

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
        middleware = [
            Middleware(cls, **kwargs) for cls, kwargs in self._middleware_stack
        ]
        from eden.context_middleware import ContextMiddleware
        middleware.insert(0, Middleware(ContextMiddleware))
        middleware.insert(1, Middleware(get_middleware_class("request")))
        from eden.error_middleware import ErrorHandlerMiddleware
        middleware.insert(2, Middleware(ErrorHandlerMiddleware))
        if self.debug and self.browser_reload:
            middleware.append(Middleware(get_middleware_class("browser_reload")))
        return middleware

    def _build_exception_handlers(self) -> dict:
        exception_handlers = {
            exc_cls: self._wrap_exception_handler(handler)
            for exc_cls, handler in self._exception_handlers.items()
            if isinstance(exc_cls, type)
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
            self._app.eden = self # type: ignore
            return self._app

    def _configure_lifespan(self) -> Callable:
        @asynccontextmanager
        async def lifespan(app: Starlette) -> AsyncGenerator[None, None]:
            await self.broker.startup()
            for handler in self._startup_handlers:
                result = handler()
                if inspect.isawaitable(result):
                    await result
            yield
            await self.broker.shutdown()
            for handler in self._shutdown_handlers:
                result = handler()
                if inspect.isawaitable(result):
                    await result
        return lifespan

    def _configure_static_files(self, routes: list) -> None:
        if os.path.isdir(self.static_dir):
            from starlette.routing import Mount
            from starlette.staticfiles import StaticFiles
            routes.append(Mount(self.static_url, app=StaticFiles(directory=self.static_dir), name="static"))

    async def _handle_exception(self, request: Request, exc: Exception) -> StarletteResponse:
        from eden.exceptions import EdenException
        if isinstance(exc, EdenException):
            return await self._exception_dispatcher.handle_eden_exception(request, exc)
        return await self._exception_dispatcher.handle_unhandled_exception(request, exc)

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

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        app = await self.build()
        await app(scope, receive, send)
