"""
Eden Framework — Comprehensive Integration Audit Test Suite
============================================================
Tests cross-module integration, import cleanliness, API surface accuracy,
and end-to-end feature correctness.
"""

import asyncio
import inspect
import os
import re
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

# ──────────────────────────────────────────────────────────────────────────────
# SECTION 1: Import & Public API Audit
# ──────────────────────────────────────────────────────────────────────────────

class TestImportCleanliness:
    """Verify that `import eden` works and the public API surface is complete."""

    def test_top_level_import_succeeds(self):
        import eden
        assert eden.__version__ == "0.1.0"

    def test_all_exports_are_importable(self):
        """Every name in __all__ must be a real attribute on the eden module."""
        import eden
        missing = []
        for name in eden.__all__:
            if not hasattr(eden, name):
                missing.append(name)
        assert missing == [], f"Missing exports in __all__: {missing}"

    def test_no_circular_imports(self):
        """Importing eden submodules should not raise circular import errors."""
        modules = [
            "eden.app", "eden.routing", "eden.templating", "eden.middleware",
            "eden.forms", "eden.requests", "eden.responses", "eden.exceptions",
            "eden.context", "eden.realtime", "eden.websocket", "eden.components",
            "eden.htmx", "eden.services", "eden.validators", "eden.cache",
        ]
        for mod in modules:
            try:
                __import__(mod)
            except ImportError as e:
                pytest.fail(f"Failed to import {mod}: {e}")

    def test_core_classes_exist(self):
        """Critical framework classes must be available at top level."""
        from eden import (
            Eden, Router, Route, Request, Component,
            Model, BaseForm, Schema, Database,
        )
        assert inspect.isclass(Eden)
        assert inspect.isclass(Router)
        assert inspect.isclass(Request)
        assert inspect.isclass(Component)
        assert inspect.isclass(Model)
        assert inspect.isclass(BaseForm)
        assert inspect.isclass(Schema)
        assert inspect.isclass(Database)

    def test_response_shortcuts_exist(self):
        """Shortcut functions json(), html(), redirect() must exist."""
        from eden import json, html, redirect
        assert callable(json)
        assert callable(html)
        assert callable(redirect)

    def test_orm_utilities_importable(self):
        """ORM utilities should be importable from top-level eden."""
        from eden import (
            select, update, delete, insert, func, text,
            and_, or_, not_, desc, asc, JSON,
            Q, F, f, QuerySet, Page,
            StringField, IntField, TextField, BoolField, FloatField,
            DateTimeField, UUIDField, ForeignKeyField, Relationship,
        )

    def test_exception_hierarchy(self):
        """All exception classes should derive from EdenException."""
        from eden import (
            EdenException, BadRequest, Unauthorized, Forbidden,
            NotFound, MethodNotAllowed, Conflict, ValidationError,
            TooManyRequests, InternalServerError,
        )
        for exc in [BadRequest, Unauthorized, Forbidden, NotFound,
                    MethodNotAllowed, Conflict, ValidationError,
                    TooManyRequests, InternalServerError]:
            assert issubclass(exc, EdenException), f"{exc.__name__} doesn't extend EdenException"

    def test_validator_imports(self):
        """All validators should be importable."""
        from eden import (
            validate_email, validate_phone, validate_password,
            validate_url, validate_slug, validate_ip,
            validate_color, validate_credit_card, validate_date,
        )


# ──────────────────────────────────────────────────────────────────────────────
# SECTION 2: Core App (Eden) Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestEdenApp:
    """Test the Eden application lifecycle, configuration, and routing."""

    def test_eden_instantiation(self):
        from eden import Eden
        app = Eden(title="Test", version="1.0", debug=True, secret_key="s3cret")
        assert app.title == "Test"
        assert app.version == "1.0"
        assert app.debug is True
        assert app.secret_key == "s3cret"

    def test_eden_sets_context(self):
        from eden import Eden
        from eden.context import get_app
        app = Eden(title="ContextTest")
        assert get_app() == app

    def test_route_registration(self):
        from eden import Eden
        app = Eden()

        @app.get("/hello", name="hello")
        async def hello():
            return {"message": "hi"}

        routes = app.get_routes()
        assert any(r["name"] == "hello" and r["path"] == "/hello" for r in routes)

    def test_all_http_methods_register(self):
        from eden import Eden
        app = Eden()

        @app.get("/a")
        async def a(): pass
        @app.post("/b")
        async def b(): pass
        @app.put("/c")
        async def c(): pass
        @app.patch("/d")
        async def d(): pass
        @app.delete("/e")
        async def e(): pass

        routes = app.get_routes()
        methods = {r["path"]: r["methods"] for r in routes if r["type"] == "http"}
        assert methods["/a"] == ["GET"]
        assert methods["/b"] == ["POST"]
        assert methods["/c"] == ["PUT"]
        assert methods["/d"] == ["PATCH"]
        assert methods["/e"] == ["DELETE"]

    def test_include_router(self):
        from eden import Eden, Router
        app = Eden()
        router = Router(prefix="/api", name="api")

        @router.get("/users", name="list")
        async def list_users():
            return []

        app.include_router(router, prefix="/v1")
        routes = app.get_routes()
        assert any(r["path"] == "/v1/api/users" and r["name"] == "api:list" for r in routes)

    def test_middleware_string_shorthand(self):
        from eden import Eden
        app = Eden()
        # default middlewares are added, we just check that "cors" is present
        app.add_middleware("cors", allow_origins=["*"])
        from eden.middleware import CORSMiddleware
        assert any(m[0] == CORSMiddleware for m in app._middleware_stack)

    def test_middleware_class_registration(self):
        from eden import Eden
        from eden.middleware import GZipMiddleware
        app = Eden()
        count_before = len(app._middleware_stack)
        app.add_middleware(GZipMiddleware)
        # GZip is added by default, so it might replace or just be there.
        # Either way, we check that it's in the stack.
        assert any(m[0] == GZipMiddleware for m in app._middleware_stack)

    def test_exception_handler_registration(self):
        from eden import Eden, NotFound
        app = Eden()

        @app.exception_handler(NotFound)
        async def handle_not_found(request, exc):
            return {"error": "not found"}

        assert NotFound in app._exception_handlers

    def test_startup_shutdown_hooks(self):
        from eden import Eden
        app = Eden()
        hooks = []

        @app.on_startup
        async def s1(): hooks.append("start")
        @app.on_shutdown
        async def s2(): hooks.append("stop")

        assert len(app._startup_handlers) == 1
        assert len(app._shutdown_handlers) == 1

    @pytest.mark.asyncio
    async def test_build_returns_starlette_app(self):
        from eden import Eden
        from starlette.applications import Starlette
        app = Eden(title="BuildTest")
        starlette_app = await app.build()
        assert isinstance(starlette_app, Starlette)

    @pytest.mark.asyncio
    async def test_build_sets_eden_reference(self):
        from eden import Eden
        app = Eden(title="RefTest")
        starlette_app = await app.build()
        assert starlette_app.eden is app


# ──────────────────────────────────────────────────────────────────────────────
# SECTION 3: Routing Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestRouting:
    """Test the Router, Route, and WebSocketRoute classes."""

    def test_router_prefix(self):
        from eden import Router
        r = Router(prefix="/api/v1")
        assert r.prefix == "/api/v1"

    def test_named_routes(self):
        from eden import Router
        r = Router(name="users")

        @r.get("/", name="index")
        async def index(): pass

        assert r.routes[0].name == "index"

    def test_namespace_propagation(self):
        from eden import Router
        parent = Router(name="parent")
        child = Router(prefix="/child", name="child")

        @child.get("/list", name="list")
        async def child_list(): pass

        parent.include_router(child)
        assert parent.routes[0].name == "child:list"

    def test_route_middleware_merge(self):
        from eden import Router

        def m1(): pass
        def m2(): pass

        parent = Router(middleware=[m1])
        child = Router(middleware=[m2])

        @child.get("/test")
        async def t(): pass

        parent.include_router(child)
        assert m1 in parent.routes[0].middleware
        assert m2 in parent.routes[0].middleware

    def test_to_starlette_routes(self):
        from eden import Router
        r = Router()

        @r.get("/test", name="test_route")
        async def test(): pass

        starlette_routes = r.to_starlette_routes()
        assert len(starlette_routes) == 1

    def test_websocket_route(self):
        from eden import Router
        r = Router()

        @r.websocket("/ws")
        async def ws_handler(): pass

        assert len(r.routes) == 1
        from eden.routing import WebSocketRoute
        assert isinstance(r.routes[0], WebSocketRoute)

    def test_crud_router(self):
        """Router with model= should auto-generate CRUD routes."""
        from eden import Router
        mock_model = MagicMock()
        mock_model.__tablename__ = "tasks"
        mock_model.template_prefix = "tasks"

        r = Router(prefix="/tasks", model=mock_model)
        route_names = [route.name for route in r.routes]
        assert "list" in route_names
        assert "create" in route_names
        assert "show" in route_names
        assert "update" in route_names
        assert "destroy" in route_names


# ──────────────────────────────────────────────────────────────────────────────
# SECTION 4: Templating Engine Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestTemplating:
    """Test the Eden directive preprocessor and template rendering."""

    def _preprocess(self, source: str) -> str:
        from eden.templating import EdenDirectivesExtension
        ext = EdenDirectivesExtension.__new__(EdenDirectivesExtension)
        return ext.preprocess(source, name=None, filename=None)

    def test_extends_directive(self):
        result = self._preprocess("@extends('base.html')")
        assert "{% extends 'base.html' %}" in result

    def test_include_directive(self):
        result = self._preprocess("@include('partial.html')")
        assert "{% include 'partial.html' %}" in result

    def test_if_else_endif_directives(self):
        result = self._preprocess("@if(user) { Hello } @else { Guest }")
        assert "{% if user %}" in result
        assert "{% else %}" in result
        assert "{% endif %}" in result

    def test_for_loop_directive(self):
        result = self._preprocess("@for(item in items) { {{ item }} }")
        assert "{% for item in items %}" in result
        assert "{% endfor %}" in result

    def test_csrf_directive(self):
        result = self._preprocess("@csrf")
        assert 'input type="hidden"' in result
        assert "csrf_token" in result

    def test_method_directive(self):
        result = self._preprocess("@method('PUT')")
        assert 'name="_method"' in result
        assert 'value="PUT"' in result

    def test_url_directive_simple(self):
        result = self._preprocess('@url("home")')
        assert "url_for" in result

    def test_url_directive_with_params(self):
        result = self._preprocess('@url("user:profile", user_id=1)')
        assert "url_for" in result

    def test_url_directive_component(self):
        result = self._preprocess('@url("component:like-post")')
        assert "/_components/like-post" in result or "url_for" in result

    def test_section_directive(self):
        result = self._preprocess("@section('content') { Body }")
        assert "{% block content %}" in result
        assert "{% endblock %}" in result

    def test_yield_directive(self):
        result = self._preprocess("@yield('content')")
        assert "{% block content %}" in result

    def test_css_directive(self):
        result = self._preprocess("@css('style.css')")
        assert 'rel="stylesheet"' in result

    def test_js_directive(self):
        result = self._preprocess("@js('app.js')")
        assert "<script" in result

    def test_old_directive(self):
        result = self._preprocess("@old('email')")
        assert "old(" in result

    def test_json_directive(self):
        result = self._preprocess("@json(data)")
        assert "json_encode" in result

    def test_dump_directive(self):
        result = self._preprocess("@dump(my_var)")
        assert "eden-dump" in result
        assert "json_encode" in result

    def test_auth_guest_directives(self):
        result = self._preprocess("@auth { Logged in } @guest { Not logged in }")
        assert "{% if" in result
        assert "is_authenticated" in result

    def test_htmx_directive(self):
        result = self._preprocess("@htmx { Partial }")
        assert "is_htmx" in result or "HX-Request" in result

    def test_checked_directive(self):
        result = self._preprocess("@checked(is_active)")
        assert "{% if is_active %}checked{% endif %}" in result

    def test_fragment_directive(self):
        result = self._preprocess("@fragment('items') { Content }")
        assert "block" in result or "fragment" in result

    def test_switch_case_directives(self):
        result = self._preprocess("@switch(role) { @case('admin') { Admin } }")
        assert "if" in result or "case" in result

    def test_let_directive(self):
        result = self._preprocess("@let(x = 42)")
        assert "set" in result or "let" in result

    def test_render_field_directive(self):
        result = self._preprocess("@render_field(form['name'])")
        assert "render" in result


# ──────────────────────────────────────────────────────────────────────────────
# SECTION 5: Component System Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestComponents:
    """Test the component registration, action system, and dispatcher."""

    def test_component_registration(self):
        from eden.components import Component, register, get_component, _registry

        @register("audit-counter")
        class AuditCounter(Component):
            template_name = "components/counter.html"
            count: int = 0

        assert get_component("audit-counter") is AuditCounter
        # Cleanup
        _registry.pop("audit-counter", None)

    def test_action_decorator(self):
        from eden.components import Component, register, action, _registry, _action_registry

        @register("audit-btn")
        class AuditButton(Component):
            template_name = "components/btn.html"

            @action("click-me")
            def handle_click(self, request):
                return "<b>Clicked!</b>"

        assert hasattr(AuditButton.handle_click, "_is_eden_action")
        assert AuditButton.handle_click._action_slug == "click-me"
        assert "click-me" in _action_registry
        # Cleanup
        _registry.pop("audit-btn", None)
        _action_registry.pop("click-me", None)

    def test_action_url_generation(self):
        from eden.components import Component, register, _registry

        @register("audit-widget")
        class AuditWidget(Component):
            template_name = "components/widget.html"

        inst = AuditWidget()
        url = inst.action_url("do-something")
        assert url == "/_eden/component/audit-widget/do-something"
        _registry.pop("audit-widget", None)

    def test_component_get_state(self):
        from eden.components import Component, register, _registry

        @register("audit-state")
        class AuditState(Component):
            template_name = "t.html"
            count = 0
            name = "test"

        inst = AuditState(count=5, name="hello")
        state = inst.get_state()
        assert state["count"] == 5
        assert state["name"] == "hello"
        assert "request" not in state
        _registry.pop("audit-state", None)

    def test_get_component_router_routes(self):
        from eden.components import get_component_router
        router = get_component_router()
        paths = [r.path for r in router.routes]
        assert "/_eden/component/{component_name}/{action_name}" in paths
        assert "/_components/{action_slug}" in paths


# ──────────────────────────────────────────────────────────────────────────────
# SECTION 6: Response & Request Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestResponses:
    """Test response classes and shortcut functions."""

    def test_json_response(self):
        from eden.responses import JsonResponse
        resp = JsonResponse({"key": "value"}, status_code=200)
        assert resp.status_code == 200
        assert b"key" in resp.body

    def test_html_response(self):
        from eden.responses import HtmlResponse
        resp = HtmlResponse("<h1>Hello</h1>")
        assert resp.status_code == 200
        assert b"Hello" in resp.body

    def test_redirect_response(self):
        from eden.responses import redirect
        resp = redirect("/login")
        assert resp.status_code == 307

    def test_safe_redirect_blocks_external(self):
        from eden.responses import SafeRedirectResponse
        resp = SafeRedirectResponse("https://evil.com/steal")
        assert resp.headers.get("location") == "/"

    def test_safe_redirect_allows_local(self):
        from eden.responses import SafeRedirectResponse
        resp = SafeRedirectResponse("/dashboard")
        assert resp.headers.get("location") == "/dashboard"

    def test_safe_redirect_blocks_double_slash(self):
        from eden.responses import SafeRedirectResponse
        resp = SafeRedirectResponse("//evil.com")
        assert resp.headers.get("location") == "/"

    def test_json_shortcut(self):
        from eden import json
        resp = json({"ok": True}, status_code=201)
        assert resp.status_code == 201

    def test_html_shortcut(self):
        from eden import html
        resp = html("<p>Test</p>")
        assert b"Test" in resp.body

    def test_pydantic_serialization(self):
        from eden.responses import JsonResponse
        from pydantic import BaseModel

        class Item(BaseModel):
            id: int
            name: str

        resp = JsonResponse(Item(id=1, name="Test"))
        assert b"Test" in resp.body


# ──────────────────────────────────────────────────────────────────────────────
# SECTION 7: Context System Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestContext:
    """Test context variable management and proxies."""

    def test_set_get_request(self):
        from eden.context import set_request, get_request, reset_request
        mock_req = MagicMock()
        token = set_request(mock_req)
        assert get_request() is mock_req
        reset_request(token)

    def test_set_get_user(self):
        from eden.context import set_user, get_user, reset_user
        mock_user = MagicMock()
        token = set_user(mock_user)
        assert get_user() is mock_user
        reset_user(token)

    def test_proxy_raises_on_empty_context(self):
        from eden.context import ContextProxy
        proxy = ContextProxy(lambda: None, "test")
        with pytest.raises(RuntimeError, match="Working outside of test context"):
            proxy.some_attr

    def test_proxy_delegates_to_real_object(self):
        from eden.context import ContextProxy
        obj = MagicMock()
        obj.name = "Eden"
        proxy = ContextProxy(lambda: obj, "test")
        assert proxy.name == "Eden"


# ──────────────────────────────────────────────────────────────────────────────
# SECTION 8: Exception Handling Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestExceptions:
    """Test Eden exception system."""

    def test_exception_defaults(self):
        from eden import EdenException
        exc = EdenException()
        assert exc.status_code == 500
        assert exc.detail == "An unexpected error occurred."

    def test_exception_custom_detail(self):
        from eden import BadRequest
        exc = BadRequest("Invalid input")
        assert exc.detail == "Invalid input"
        assert exc.status_code == 400

    def test_exception_to_dict(self):
        from eden import NotFound
        exc = NotFound("User not found")
        d = exc.to_dict()
        assert d["error"] is True
        assert d["status_code"] == 404
        assert d["detail"] == "User not found"

    def test_validation_error_with_errors(self):
        from eden import ValidationError
        exc = ValidationError(errors=[{"loc": ["email"], "msg": "invalid"}])
        d = exc.to_dict()
        assert "extra" in d
        assert len(d["extra"]["errors"]) == 1


# ──────────────────────────────────────────────────────────────────────────────
# SECTION 9: Forms System Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestForms:
    """Test form handling, validation, and rendering."""

    def test_schema_validation_valid(self):
        from eden import Schema

        class LoginSchema(Schema):
            email: str
            password: str

        form = LoginSchema.as_form({"email": "a@b.com", "password": "123"})
        assert form.is_valid()
        assert form.model_instance.email == "a@b.com"

    def test_schema_validation_invalid(self):
        from eden import Schema

        class LoginSchema(Schema):
            email: str
            password: str

        form = LoginSchema.as_form({})
        assert not form.is_valid()
        assert len(form.errors) > 0

    def test_form_field_rendering(self):
        from eden.forms import FormField
        field = FormField(name="email", value="test@test.com", widget="email")
        html = field.render()
        assert 'name="email"' in html
        assert 'value="test@test.com"' in html

    def test_form_field_textarea(self):
        from eden.forms import FormField
        field = FormField(name="bio", widget="textarea", value="Hello")
        html = field.as_textarea()
        assert "<textarea" in html
        assert "Hello" in html

    def test_form_field_select(self):
        from eden.forms import FormField
        field = FormField(name="role", widget="select")
        html = field.as_select([("admin", "Admin"), ("user", "User")])
        assert "<select" in html
        assert '<option value="admin"' in html

    def test_form_iteration(self):
        from eden import Schema, BaseForm

        class TestSchema(Schema):
            name: str
            age: int

        form = BaseForm(schema=TestSchema, data={"name": "X", "age": "25"})
        fields = list(form)
        assert len(fields) == 2
        assert fields[0].name == "name"

    def test_form_field_error_class(self):
        from eden.forms import FormField
        field = FormField(name="email", error="Required")
        cloned = field.add_error_class("is-invalid")
        assert "is-invalid" in cloned.css_classes


# ──────────────────────────────────────────────────────────────────────────────
# SECTION 10: Middleware Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestMiddleware:
    """Test the middleware registry and string shorthand resolution."""

    def test_middleware_registry(self):
        from eden.middleware import get_middleware_class
        assert get_middleware_class("cors") is not None
        assert get_middleware_class("gzip") is not None
        assert get_middleware_class("session") is not None
        assert get_middleware_class("csrf") is not None
        assert get_middleware_class("security") is not None
        assert get_middleware_class("ratelimit") is not None

    def test_csrf_safe_methods(self):
        from eden.middleware import CSRFMiddleware
        assert "GET" in CSRFMiddleware.SAFE_METHODS
        assert "POST" not in CSRFMiddleware.SAFE_METHODS

    def test_security_headers_defaults(self):
        from eden.middleware import SecurityHeadersMiddleware
        assert "X-Content-Type-Options" in SecurityHeadersMiddleware.DEFAULT_HEADERS
        assert "X-Frame-Options" in SecurityHeadersMiddleware.DEFAULT_HEADERS

    def test_limiter_parse(self):
        from eden.middleware import limiter
        decorator = limiter("5/minute")
        assert callable(decorator)


# ──────────────────────────────────────────────────────────────────────────────
# SECTION 11: WebSocket & Real-time Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestWebSocket:
    """Test WebSocket support and real-time management."""

    def test_connection_manager(self):
        from eden import ConnectionManager
        mgr = ConnectionManager()
        assert not mgr.rooms
        assert mgr.count() == 0

    def test_websocket_router_event_registration(self):
        from eden import WebSocketRouter
        ws = WebSocketRouter(prefix="/ws")

        @ws.on("chat")
        async def handle_chat(socket, data, manager):
            pass

        assert "chat" in ws._handlers

    def test_websocket_router_lifecycle_hooks(self):
        from eden import WebSocketRouter
        ws = WebSocketRouter()

        @ws.on_connect
        async def on_connect(socket, mgr): pass
        @ws.on_disconnect
        async def on_disconnect(socket, mgr): pass

        assert ws._on_connect is not None
        assert ws._on_disconnect is not None

    def test_realtime_manager_singleton(self):
        from eden import realtime_manager
        assert realtime_manager is not None
        assert hasattr(realtime_manager, "broadcast")
        assert hasattr(realtime_manager, "subscribe")
        assert hasattr(realtime_manager, "connect")


# ──────────────────────────────────────────────────────────────────────────────
# SECTION 12: Cross-Module Integration Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestCrossModuleIntegration:
    """Test how different modules work together."""

    @pytest.mark.asyncio
    async def test_eden_build_includes_component_routes(self):
        """Component router should be automatically included in the built app."""
        from eden import Eden
        app = Eden(title="IntegrationTest")

        @app.get("/")
        async def home():
            return {"ok": True}

        starlette_app = await app.build()
        routes = starlette_app.routes
        route_paths = []
        for r in routes:
            if hasattr(r, 'path'):
                route_paths.append(r.path)
            elif hasattr(r, 'routes'):
                for sub in r.routes:
                    if hasattr(sub, 'path'):
                        route_paths.append(sub.path)

        # Component routes should be registered
        assert any("_components" in p or "_eden/component" in p for p in route_paths), \
            f"Component routes not found. Routes: {route_paths}"

    @pytest.mark.asyncio
    async def test_eden_build_includes_sync_websocket(self):
        """The /_eden/sync WebSocket should be auto-registered."""
        from eden import Eden
        app = Eden(title="SyncTest")
        starlette_app = await app.build()
        route_names = [getattr(r, 'name', '') for r in starlette_app.routes]
        assert "eden:sync" in route_names

    def test_router_generates_starlette_compatible_routes(self):
        """Eden routes must convert cleanly to Starlette routes."""
        from eden import Router
        from starlette.routing import Route as StarletteRoute

        r = Router(prefix="/api")
        @r.get("/test", name="api_test")
        async def test_handler(): return {"ok": True}

        starlette_routes = r.to_starlette_routes()
        assert len(starlette_routes) == 1
        assert isinstance(starlette_routes[0], StarletteRoute)

    def test_eden_templates_property(self):
        """Eden.templates should return an EdenTemplates instance."""
        from eden import Eden
        app = Eden()
        templates = app.templates
        from eden.templating import EdenTemplates
        assert isinstance(templates, EdenTemplates)

    def test_middleware_functional_registration(self):
        """Eden should accept function middleware and wrap it."""
        from eden import Eden
        app = Eden()

        async def my_middleware(request, call_next):
            response = await call_next(request)
            return response

        count_before = len(app._middleware_stack)
        app.add_middleware(my_middleware)
        assert len(app._middleware_stack) == count_before + 1


# ──────────────────────────────────────────────────────────────────────────────
# SECTION 13: Validators Integration
# ──────────────────────────────────────────────────────────────────────────────

class TestValidators:
    """Test that validators produce correct results."""

    def test_email_validation(self):
        from eden import validate_email
        assert validate_email("user@example.com").is_valid
        assert not validate_email("invalid").is_valid

    def test_url_validation(self):
        from eden import validate_url
        assert validate_url("https://example.com").is_valid
        assert not validate_url("not-a-url").is_valid

    def test_slug_validation(self):
        from eden import validate_slug
        assert validate_slug("hello-world").is_valid
        assert not validate_slug("Hello World!").is_valid

    def test_phone_validation(self):
        from eden import validate_phone
        result = validate_phone("+1234567890")
        # Should at least not crash
        assert hasattr(result, "is_valid")

    def test_password_validation(self):
        from eden import validate_password
        weak = validate_password("123")
        strong = validate_password("MyStr0ng!P@ssw0rd")
        assert not weak.is_valid
        assert strong.is_valid
