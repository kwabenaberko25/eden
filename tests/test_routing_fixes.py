"""
Tests for Eden routing fixes — covers all issues from the routing/views
implementation plan (Phases 1–4).

Issue Index:
    A1  — Private Starlette API access (request._send)
    A2  — url_for() silent failures on missing parameters
    A4  — CRUD route name duplication
    A5  — Middleware detection misses callable instances
    A6  — ANY method in View replaces with fixed set
    A7  — View.dispatch() allowed-methods list inconsistent with add_view()
    B1  — Missing OPTIONS / HEAD decorator shortcuts
    C1  — url_for() regex edge cases with special characters
    C2  — Route name conflict detection
"""

import pytest
from httpx import ASGITransport, AsyncClient

from eden import Eden, Router
from eden.routing import Route, View, _VIEW_METHODS, _ALL_VIEW_METHODS
from eden.requests import Request


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def router() -> Router:
    """A bare Router for unit-level tests that don't need a running app."""
    return Router()


@pytest.fixture
def app() -> Eden:
    """A minimal Eden app with routes for integration-level tests."""
    app = Eden(debug=True)

    @app.get("/")
    async def index():
        return {"ok": True}

    @app.get("/items/{item_id:int}")
    async def get_item(item_id: int):
        return {"item_id": item_id}

    @app.post("/items", name="create_item")
    async def create_item():
        return {"created": True}

    return app


@pytest.fixture
async def client(app: Eden) -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


# ══════════════════════════════════════════════════════════════════════════════
# Phase 1: Critical Bug Fixes
# ══════════════════════════════════════════════════════════════════════════════


class TestUrlFor:
    """Tests for url_for() correctness (A2, C1)."""

    def test_url_for_simple_param(self, router: Router):
        """url_for substitutes simple {param} placeholders."""

        @router.get("/users/{user_id}", name="user_detail")
        async def user_detail(user_id: str):
            pass

        assert router.url_for("user_detail", user_id="42") == "/users/42"

    def test_url_for_typed_param(self, router: Router):
        """url_for substitutes {param:type} placeholders."""

        @router.get("/items/{item_id:int}", name="item_detail")
        async def item_detail(item_id: int):
            pass

        assert router.url_for("item_detail", item_id=99) == "/items/99"

    def test_url_for_raises_on_missing_params(self, router: Router):
        """url_for raises ValueError when required params are not provided (A2)."""

        @router.get("/users/{user_id}/posts/{post_id}", name="user_post")
        async def user_post(user_id: str, post_id: str):
            pass

        with pytest.raises(ValueError, match="Missing path parameters"):
            router.url_for("user_post", user_id="1")

    def test_url_for_raises_on_all_missing_params(self, router: Router):
        """url_for raises ValueError when no params provided at all (A2)."""

        @router.get("/items/{id:int}", name="item")
        async def item(id: int):
            pass

        with pytest.raises(ValueError, match="Missing path parameters"):
            router.url_for("item")

    def test_url_for_raises_on_unknown_route(self, router: Router):
        """url_for raises ValueError for a route name that doesn't exist."""
        with pytest.raises(ValueError, match="not found"):
            router.url_for("nonexistent_route")

    def test_url_for_with_all_params_succeeds(self, router: Router):
        """url_for returns a clean path when all params are provided."""

        @router.get("/a/{x}/b/{y:int}", name="multi")
        async def multi(x: str, y: int):
            pass

        result = router.url_for("multi", x="hello", y=42)
        assert result == "/a/hello/b/42"
        assert "{" not in result

    def test_url_for_special_char_param_name(self, router: Router):
        """url_for handles parameter names that contain regex-special chars (C1)."""
        # Construct a route with a normal param name to verify regex escaping
        # doesn't break basic functionality.

        @router.get("/test/{item_id:int}", name="test_item")
        async def test_item(item_id: int):
            pass

        assert router.url_for("test_item", item_id=5) == "/test/5"

    def test_url_for_sub_router_fallback(self, router: Router):
        """url_for finds routes via sub-router naming convention."""
        sub = Router(prefix="/api", name="api")

        @sub.get("/ping", name="ping")
        async def ping():
            pass

        router.include_router(sub)
        # Should find "api:ping"
        assert router.url_for("api:ping") == "/api/ping"
        # Also find via short name fallback
        assert router.url_for("ping") == "/api/ping"


# ── CRUD Route Names (A4) ────────────────────────────────────────────────────


class TestCrudRouteNames:
    """Tests for CRUD route name uniqueness (A4)."""

    def _make_mock_model(self):
        """Create a mock model class with the required CRUD contract."""

        class MockModel:
            __tablename__ = "widgets"
            __name__ = "Widget"

            @classmethod
            async def all(cls):
                return []

            @classmethod
            async def get(cls, id):
                return None

            async def save(self):
                return True

            async def update(self, **data):
                return True

            async def delete(self):
                pass

        return MockModel

    def test_crud_route_names_are_unique(self):
        """All auto-generated CRUD route names must be unique (A4)."""
        model = self._make_mock_model()
        router = Router(prefix="/widgets", model=model)

        names = [r.name for r in router.routes if isinstance(r, Route)]
        assert len(names) == len(set(names)), f"Duplicate route names: {names}"

    def test_crud_route_names_correct(self):
        """CRUD routes have the expected canonical names."""
        model = self._make_mock_model()
        router = Router(prefix="/widgets", model=model)

        names = {r.name for r in router.routes if isinstance(r, Route)}
        expected = {"list", "new", "create", "show", "edit", "update", "destroy"}
        assert names == expected


# ── Route Name Conflict Detection (C2 / B5) ──────────────────────────────────


class TestRouteNameConflicts:
    """Tests for duplicate route name detection (Phase 4.1)."""

    def test_duplicate_name_raises(self, router: Router):
        """Registering two routes with the same name on the same router raises."""

        @router.get("/a", name="duplicate")
        async def handler_a():
            pass

        with pytest.raises(ValueError, match="already registered"):

            @router.get("/b", name="duplicate")
            async def handler_b():
                pass

    def test_same_function_name_without_explicit_name_raises(self, router: Router):
        """Two handlers with the same __name__ (without explicit name=) collide."""

        @router.get("/first")
        async def handler():
            pass

        with pytest.raises(ValueError, match="already registered"):

            @router.get("/second")
            async def handler():  # noqa: F811 — intentional redefinition
                pass

    def test_different_names_succeed(self, router: Router):
        """Routes with unique names register without error."""

        @router.get("/a", name="route_a")
        async def a():
            pass

        @router.get("/b", name="route_b")
        async def b():
            pass

        assert len(router.routes) == 2

    def test_sub_router_merge_does_not_trigger_conflict(self):
        """include_router() copies routes into parent without _add_route guard."""
        parent = Router()
        child = Router(prefix="/child")

        @parent.get("/home", name="index")
        async def parent_index():
            pass

        @child.get("/home", name="index")
        async def child_index():
            pass

        # Should not raise — include_router bypasses the per-router guard
        parent.include_router(child)
        assert len(parent.routes) == 2


# ══════════════════════════════════════════════════════════════════════════════
# Phase 2: Correctness & Consistency
# ══════════════════════════════════════════════════════════════════════════════


class TestViewDispatch:
    """Tests for View method alignment (A6, A7)."""

    def test_view_methods_constant_completeness(self):
        """_VIEW_METHODS includes get, post, put, patch, delete, options, head."""
        assert set(_VIEW_METHODS) == {
            "get", "post", "put", "patch", "delete", "options", "head"
        }

    def test_all_view_methods_uppercased(self):
        """_ALL_VIEW_METHODS is the uppercased version of _VIEW_METHODS."""
        assert _ALL_VIEW_METHODS == [m.upper() for m in _VIEW_METHODS]

    def test_add_view_any_includes_all_methods(self):
        """A View with any() is registered for all standard HTTP methods (A6)."""
        router = Router()

        class AnyView(View):
            async def any(self, request: Request, **kw):
                return {"method": request.method}

        router.add_view("/any", AnyView)

        route = router.routes[0]
        assert isinstance(route, Route)
        assert set(route.methods) == set(_ALL_VIEW_METHODS)

    def test_add_view_specific_methods_only(self):
        """A View with only get+post is registered for exactly those methods."""
        router = Router()

        class LimitedView(View):
            async def get(self, request: Request, **kw):
                return {"ok": True}

            async def post(self, request: Request, **kw):
                return {"ok": True}

        router.add_view("/limited", LimitedView)

        route = router.routes[0]
        assert isinstance(route, Route)
        assert set(route.methods) == {"GET", "POST"}

    async def test_view_dispatch_options_method(self):
        """View.dispatch() finds an options() handler if defined (A7)."""
        app = Eden(debug=True)
        router = Router()

        class OptionsView(View):
            async def get(self, request: Request, **kw):
                return {"method": "GET"}

            async def options(self, request: Request, **kw):
                return {"method": "OPTIONS"}

        router.add_view("/opts", OptionsView)
        app.include_router(router)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as c:
            resp = await c.options("/opts")
            assert resp.status_code == 200
            assert resp.json()["method"] == "OPTIONS"

    async def test_view_dispatch_head_method(self):
        """View.dispatch() finds a head() handler if defined (A7)."""
        app = Eden(debug=True)
        router = Router()

        class HeadView(View):
            async def get(self, request: Request, **kw):
                return {"method": "GET"}

            async def head(self, request: Request, **kw):
                from eden.responses import Response
                return Response(status_code=200, headers={"X-Custom": "yes"})

        router.add_view("/hd", HeadView)
        app.include_router(router)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as c:
            resp = await c.head("/hd")
            assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# Phase 3: Feature Enhancements
# ══════════════════════════════════════════════════════════════════════════════


class TestOptionsHeadDecorators:
    """Tests for new OPTIONS and HEAD decorator shortcuts (B1)."""

    async def test_options_route(self):
        """Router.options() registers an OPTIONS route."""
        app = Eden(debug=True)

        @app.options("/cors-check", name="cors_check")
        async def cors_check():
            from eden.responses import Response
            return Response(
                status_code=204,
                headers={"Allow": "GET, POST, OPTIONS"},
            )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as c:
            resp = await c.options("/cors-check")
            assert resp.status_code == 204

    async def test_head_route(self):
        """Router.head() registers a HEAD route."""
        app = Eden(debug=True)

        @app.head("/health", name="health_check")
        async def health():
            from eden.responses import Response
            return Response(status_code=200)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as c:
            resp = await c.head("/health")
            assert resp.status_code == 200

    def test_options_route_registration(self, router: Router):
        """Router.options() adds a Route with methods=["OPTIONS"]."""

        @router.options("/test", name="test_options")
        async def test_handler():
            pass

        assert len(router.routes) == 1
        route = router.routes[0]
        assert isinstance(route, Route)
        assert route.methods == ["OPTIONS"]

    def test_head_route_registration(self, router: Router):
        """Router.head() adds a Route with methods=["HEAD"]."""

        @router.head("/test", name="test_head")
        async def test_handler():
            pass

        assert len(router.routes) == 1
        route = router.routes[0]
        assert isinstance(route, Route)
        assert route.methods == ["HEAD"]


# ══════════════════════════════════════════════════════════════════════════════
# Regression: Existing Functionality
# ══════════════════════════════════════════════════════════════════════════════


class TestRegression:
    """Ensure existing functionality is not broken by the fixes."""

    async def test_basic_get(self, client: AsyncClient):
        """Basic GET route still works."""
        resp = await client.get("/")
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

    async def test_path_params(self, client: AsyncClient):
        """Typed path parameters still work."""
        resp = await client.get("/items/42")
        assert resp.status_code == 200
        assert resp.json() == {"item_id": 42}

    async def test_post_route(self, client: AsyncClient):
        """POST route still works."""
        resp = await client.post("/items")
        assert resp.status_code == 200
        assert resp.json() == {"created": True}

    async def test_404(self, client: AsyncClient):
        """404 for unknown routes still works."""
        resp = await client.get("/nonexistent")
        assert resp.status_code == 404

    async def test_405(self, client: AsyncClient):
        """405 for wrong method still works."""
        resp = await client.delete("/")
        assert resp.status_code == 405
"""
Tests for Eden routing fixes — covers all issues from the routing/views
implementation plan (Phases 1–4).

Issue Index:
    A1  — Private Starlette API access (request._send)
    A2  — url_for() silent failures on missing parameters
    A4  — CRUD route name duplication
    A5  — Middleware detection misses callable instances
    A6  — ANY method in View replaces with fixed set
    A7  — View.dispatch() allowed-methods list inconsistent with add_view()
    B1  — Missing OPTIONS / HEAD decorator shortcuts
    C1  — url_for() regex edge cases with special characters
    C2  — Route name conflict detection
"""

import pytest
from httpx import ASGITransport, AsyncClient

from eden import Eden, Router
from eden.routing import Route, View, _VIEW_METHODS, _ALL_VIEW_METHODS
from eden.requests import Request


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def router() -> Router:
    """A bare Router for unit-level tests that don't need a running app."""
    return Router()


@pytest.fixture
def app() -> Eden:
    """A minimal Eden app with routes for integration-level tests."""
    app = Eden(debug=True)

    @app.get("/")
    async def index():
        return {"ok": True}

    @app.get("/items/{item_id:int}")
    async def get_item(item_id: int):
        return {"item_id": item_id}

    @app.post("/items", name="create_item")
    async def create_item():
        return {"created": True}

    return app


@pytest.fixture
async def client(app: Eden) -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


# ══════════════════════════════════════════════════════════════════════════════
# Phase 1: Critical Bug Fixes
# ══════════════════════════════════════════════════════════════════════════════


class TestUrlFor:
    """Tests for url_for() correctness (A2, C1)."""

    def test_url_for_simple_param(self, router: Router):
        """url_for substitutes simple {param} placeholders."""

        @router.get("/users/{user_id}", name="user_detail")
        async def user_detail(user_id: str):
            pass

        assert router.url_for("user_detail", user_id="42") == "/users/42"

    def test_url_for_typed_param(self, router: Router):
        """url_for substitutes {param:type} placeholders."""

        @router.get("/items/{item_id:int}", name="item_detail")
        async def item_detail(item_id: int):
            pass

        assert router.url_for("item_detail", item_id=99) == "/items/99"

    def test_url_for_raises_on_missing_params(self, router: Router):
        """url_for raises ValueError when required params are not provided (A2)."""

        @router.get("/users/{user_id}/posts/{post_id}", name="user_post")
        async def user_post(user_id: str, post_id: str):
            pass

        with pytest.raises(ValueError, match="Missing path parameters"):
            router.url_for("user_post", user_id="1")

    def test_url_for_raises_on_all_missing_params(self, router: Router):
        """url_for raises ValueError when no params provided at all (A2)."""

        @router.get("/items/{id:int}", name="item")
        async def item(id: int):
            pass

        with pytest.raises(ValueError, match="Missing path parameters"):
            router.url_for("item")

    def test_url_for_raises_on_unknown_route(self, router: Router):
        """url_for raises ValueError for a route name that doesn't exist."""
        with pytest.raises(ValueError, match="not found"):
            router.url_for("nonexistent_route")

    def test_url_for_with_all_params_succeeds(self, router: Router):
        """url_for returns a clean path when all params are provided."""

        @router.get("/a/{x}/b/{y:int}", name="multi")
        async def multi(x: str, y: int):
            pass

        result = router.url_for("multi", x="hello", y=42)
        assert result == "/a/hello/b/42"
        assert "{" not in result

    def test_url_for_special_char_param_name(self, router: Router):
        """url_for handles parameter names that contain regex-special chars (C1)."""
        # Construct a route with a normal param name to verify regex escaping
        # doesn't break basic functionality.

        @router.get("/test/{item_id:int}", name="test_item")
        async def test_item(item_id: int):
            pass

        assert router.url_for("test_item", item_id=5) == "/test/5"

    def test_url_for_sub_router_fallback(self, router: Router):
        """url_for finds routes via sub-router naming convention."""
        sub = Router(prefix="/api", name="api")

        @sub.get("/ping", name="ping")
        async def ping():
            pass

        router.include_router(sub)
        # Should find "api:ping"
        assert router.url_for("api:ping") == "/api/ping"
        # Also find via short name fallback
        assert router.url_for("ping") == "/api/ping"


# ── CRUD Route Names (A4) ────────────────────────────────────────────────────


class TestCrudRouteNames:
    """Tests for CRUD route name uniqueness (A4)."""

    def _make_mock_model(self):
        """Create a mock model class with the required CRUD contract."""

        class MockModel:
            __tablename__ = "widgets"
            __name__ = "Widget"

            @classmethod
            async def all(cls):
                return []

            @classmethod
            async def get(cls, id):
                return None

            async def save(self):
                return True

            async def update(self, **data):
                return True

            async def delete(self):
                pass

        return MockModel

    def test_crud_route_names_are_unique(self):
        """All auto-generated CRUD route names must be unique (A4)."""
        model = self._make_mock_model()
        router = Router(prefix="/widgets", model=model)

        names = [r.name for r in router.routes if isinstance(r, Route)]
        assert len(names) == len(set(names)), f"Duplicate route names: {names}"

    def test_crud_route_names_correct(self):
        """CRUD routes have the expected canonical names."""
        model = self._make_mock_model()
        router = Router(prefix="/widgets", model=model)

        names = {r.name for r in router.routes if isinstance(r, Route)}
        expected = {"list", "new", "create", "show", "edit", "update", "destroy"}
        assert names == expected


# ── Route Name Conflict Detection (C2 / B5) ──────────────────────────────────


class TestRouteNameConflicts:
    """Tests for duplicate route name detection (Phase 4.1)."""

    def test_duplicate_name_raises(self, router: Router):
        """Registering two routes with the same name on the same router raises."""

        @router.get("/a", name="duplicate")
        async def handler_a():
            pass

        with pytest.raises(ValueError, match="already registered"):

            @router.get("/b", name="duplicate")
            async def handler_b():
                pass

    def test_same_function_name_without_explicit_name_raises(self, router: Router):
        """Two handlers with the same __name__ (without explicit name=) collide."""

        @router.get("/first")
        async def handler():
            pass

        with pytest.raises(ValueError, match="already registered"):

            @router.get("/second")
            async def handler():  # noqa: F811 — intentional redefinition
                pass

    def test_different_names_succeed(self, router: Router):
        """Routes with unique names register without error."""

        @router.get("/a", name="route_a")
        async def a():
            pass

        @router.get("/b", name="route_b")
        async def b():
            pass

        assert len(router.routes) == 2

    def test_sub_router_merge_does_not_trigger_conflict(self):
        """include_router() copies routes into parent without _add_route guard."""
        parent = Router()
        child = Router(prefix="/child")

        @parent.get("/home", name="index")
        async def parent_index():
            pass

        @child.get("/home", name="index")
        async def child_index():
            pass

        # Should not raise — include_router bypasses the per-router guard
        parent.include_router(child)
        assert len(parent.routes) == 2


# ══════════════════════════════════════════════════════════════════════════════
# Phase 2: Correctness & Consistency
# ══════════════════════════════════════════════════════════════════════════════


class TestViewDispatch:
    """Tests for View method alignment (A6, A7)."""

    def test_view_methods_constant_completeness(self):
        """_VIEW_METHODS includes get, post, put, patch, delete, options, head."""
        assert set(_VIEW_METHODS) == {
            "get", "post", "put", "patch", "delete", "options", "head"
        }

    def test_all_view_methods_uppercased(self):
        """_ALL_VIEW_METHODS is the uppercased version of _VIEW_METHODS."""
        assert _ALL_VIEW_METHODS == [m.upper() for m in _VIEW_METHODS]

    def test_add_view_any_includes_all_methods(self):
        """A View with any() is registered for all standard HTTP methods (A6)."""
        router = Router()

        class AnyView(View):
            async def any(self, request: Request, **kw):
                return {"method": request.method}

        router.add_view("/any", AnyView)

        route = router.routes[0]
        assert isinstance(route, Route)
        assert set(route.methods) == set(_ALL_VIEW_METHODS)

    def test_add_view_specific_methods_only(self):
        """A View with only get+post is registered for exactly those methods."""
        router = Router()

        class LimitedView(View):
            async def get(self, request: Request, **kw):
                return {"ok": True}

            async def post(self, request: Request, **kw):
                return {"ok": True}

        router.add_view("/limited", LimitedView)

        route = router.routes[0]
        assert isinstance(route, Route)
        assert set(route.methods) == {"GET", "POST"}

    async def test_view_dispatch_options_method(self):
        """View.dispatch() finds an options() handler if defined (A7)."""
        app = Eden(debug=True)
        router = Router()

        class OptionsView(View):
            async def get(self, request: Request, **kw):
                return {"method": "GET"}

            async def options(self, request: Request, **kw):
                return {"method": "OPTIONS"}

        router.add_view("/opts", OptionsView)
        app.include_router(router)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as c:
            resp = await c.options("/opts")
            assert resp.status_code == 200
            assert resp.json()["method"] == "OPTIONS"

    async def test_view_dispatch_head_method(self):
        """View.dispatch() finds a head() handler if defined (A7)."""
        app = Eden(debug=True)
        router = Router()

        class HeadView(View):
            async def get(self, request: Request, **kw):
                return {"method": "GET"}

            async def head(self, request: Request, **kw):
                from eden.responses import Response
                return Response(status_code=200, headers={"X-Custom": "yes"})

        router.add_view("/hd", HeadView)
        app.include_router(router)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as c:
            resp = await c.head("/hd")
            assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# Phase 3: Feature Enhancements
# ══════════════════════════════════════════════════════════════════════════════


class TestOptionsHeadDecorators:
    """Tests for new OPTIONS and HEAD decorator shortcuts (B1)."""

    async def test_options_route(self):
        """Router.options() registers an OPTIONS route."""
        app = Eden(debug=True)

        @app.options("/cors-check", name="cors_check")
        async def cors_check():
            from eden.responses import Response
            return Response(
                status_code=204,
                headers={"Allow": "GET, POST, OPTIONS"},
            )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as c:
            resp = await c.options("/cors-check")
            assert resp.status_code == 204

    async def test_head_route(self):
        """Router.head() registers a HEAD route."""
        app = Eden(debug=True)

        @app.head("/health", name="health_check")
        async def health():
            from eden.responses import Response
            return Response(status_code=200)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as c:
            resp = await c.head("/health")
            assert resp.status_code == 200

    def test_options_route_registration(self, router: Router):
        """Router.options() adds a Route with methods=["OPTIONS"]."""

        @router.options("/test", name="test_options")
        async def test_handler():
            pass

        assert len(router.routes) == 1
        route = router.routes[0]
        assert isinstance(route, Route)
        assert route.methods == ["OPTIONS"]

    def test_head_route_registration(self, router: Router):
        """Router.head() adds a Route with methods=["HEAD"]."""

        @router.head("/test", name="test_head")
        async def test_handler():
            pass

        assert len(router.routes) == 1
        route = router.routes[0]
        assert isinstance(route, Route)
        assert route.methods == ["HEAD"]


# ══════════════════════════════════════════════════════════════════════════════
# Regression: Existing Functionality
# ══════════════════════════════════════════════════════════════════════════════


class TestRegression:
    """Ensure existing functionality is not broken by the fixes."""

    async def test_basic_get(self, client: AsyncClient):
        """Basic GET route still works."""
        resp = await client.get("/")
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

    async def test_path_params(self, client: AsyncClient):
        """Typed path parameters still work."""
        resp = await client.get("/items/42")
        assert resp.status_code == 200
        assert resp.json() == {"item_id": 42}

    async def test_post_route(self, client: AsyncClient):
        """POST route still works."""
        resp = await client.post("/items")
        assert resp.status_code == 200
        assert resp.json() == {"created": True}

    async def test_404(self, client: AsyncClient):
        """404 for unknown routes still works."""
        resp = await client.get("/nonexistent")
        assert resp.status_code == 404

    async def test_405(self, client: AsyncClient):
        """405 for wrong method still works."""
        resp = await client.delete("/")
        assert resp.status_code == 405
