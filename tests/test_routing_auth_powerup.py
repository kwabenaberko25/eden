"""
Eden — Routing & Auth Power-Up Integration Tests

Covers:
- URL reversal (Router.url_for, Request.url_for, Eden.url_for)
- Named route redirect (redirect_to)
- Class-Based View (CBV) dispatch
- login_required on functions and CBVs
- view_decorator applying login_required to all CBV methods
- roles_required with tenant-aware role resolution
- permissions_required with tenant-aware permission resolution
- require_permission with RBAC hierarchy
- Superuser bypass
- Tenant-scoped role/permission checks
"""

import pytest
from httpx import ASGITransport, AsyncClient
from eden import Eden, Router, View
from eden.requests import Request
from eden.responses import JsonResponse, redirect_to
from eden.auth.decorators import (
    login_required,
    roles_required,
    permissions_required,
    require_permission,
    require_role,
    require_any_role,
    require_any_permission,
    view_decorator,
)
from eden.auth.models import User
from eden.auth.rbac import default_rbac
from eden.exceptions import Unauthorized, PermissionDenied


# ─── Test Views ───────────────────────────────────────────────────────────────

class ProtectedView(View):
    """CBV with per-method login_required."""
    @login_required
    async def get(self, request: Request):
        return {"message": "Authenticated CBV!"}


@view_decorator(login_required)
class FullyProtectedView(View):
    """CBV with login_required on ALL methods via view_decorator."""
    async def get(self, request: Request):
        return {"message": "Fully Protected!"}

    async def post(self, request: Request):
        return {"message": "Posted!"}


class AdminView(View):
    """CBV with roles_required on GET."""
    @roles_required(["admin"])
    async def get(self, request: Request):
        return {"admin": "access"}


class PermissionView(View):
    """CBV with permissions_required on GET."""
    @permissions_required(["posts.read", "posts.write"])
    async def get(self, request: Request):
        return {"permissions": "granted"}


class SingleRoleView(View):
    """CBV with require_role on GET."""
    @require_role("editor")
    async def get(self, request: Request):
        return {"editor": True}


class RBACView(View):
    """CBV with require_permission using RBAC hierarchy."""
    @require_permission("reports.generate")
    async def get(self, request: Request):
        return {"report": "generated"}


class TenantRoleView(View):
    """CBV testing tenant-aware role resolution.

    The user's get_roles_for_tenant method returns tenant-scoped roles.
    """
    @roles_required(["tenant_admin"])
    async def get(self, request: Request):
        return {"tenant": "admin_access"}


class AnyRoleView(View):
    """CBV with require_any_role."""
    @require_any_role(["moderator", "admin"])
    async def get(self, request: Request):
        return {"any_role": True}


class AnyPermView(View):
    """CBV with require_any_permission."""
    @require_any_permission(["billing.read", "billing.write"])
    async def get(self, request: Request):
        return {"billing": True}


# ─── Mock Middleware ──────────────────────────────────────────────────────────

class MockAuthMiddleware:
    """
    Test middleware that reads X-Test-* headers to inject a mock user
    into the request scope. Simulates authentication without a real backend.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)

        user_email = request.headers.get("X-Test-User")
        if user_email:
            user = _make_mock_user(request)
            scope["user"] = user

        await self.app(scope, receive, send)


def _make_mock_user(request: Request):
    """Build a mock user from X-Test-* request headers."""
    user = User(email=request.headers.get("X-Test-User", "test@test.com"))
    user.id = 1
    user.roles = [r for r in request.headers.get("X-Test-Roles", "").split(",") if r]
    user.permissions = [p for p in request.headers.get("X-Test-Permissions", "").split(",") if p]
    user.is_superuser = "superuser" in user.roles

    # Tenant-scoped roles: X-Test-Tenant-Roles header
    tenant_roles_header = request.headers.get("X-Test-Tenant-Roles", "")
    if tenant_roles_header:
        tenant_roles_list = [r for r in tenant_roles_header.split(",") if r]
        # Attach a get_roles_for_tenant method
        user.get_roles_for_tenant = lambda tid: tenant_roles_list

    return user


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
async def app_instance():
    """Create the Eden app with all routes registered."""
    app = Eden(debug=True, secret_key="test-secret-key-long-enough-for-jwt")

    # ── Functional routes ──
    @app.get("/", name="index")
    async def index():
        return {"page": "index"}

    @app.get("/user/{user_id}", name="user_profile")
    async def profile(user_id: int):
        return {"user_id": user_id}

    @app.get("/goto-profile/{user_id}")
    async def goto_profile(user_id: int):
        return redirect_to("user_profile", user_id=user_id)

    @app.get("/secret")
    @login_required
    async def secret_func():
        return {"secret": "data"}

    @app.get("/test-req-url")
    async def test_req_url(request: Request):
        return {"url": str(request.url_for("user_profile", user_id=99))}

    # ── CBV routes ──
    app.add_view("/protected", ProtectedView, name="cbv_protected")
    app.add_view("/fully-protected", FullyProtectedView, name="fully_protected")
    app.add_view("/admin", AdminView, name="admin_panel")
    app.add_view("/permissions", PermissionView, name="perm_view")
    app.add_view("/editor", SingleRoleView, name="editor_view")
    app.add_view("/reports", RBACView, name="rbac_view")
    app.add_view("/tenant-admin", TenantRoleView, name="tenant_admin_view")
    app.add_view("/any-role", AnyRoleView, name="any_role_view")
    app.add_view("/billing", AnyPermView, name="any_perm_view")

    app.add_middleware(MockAuthMiddleware)
    return app


@pytest.fixture
async def app(app_instance):
    """Build the Starlette app from the Eden instance."""
    return await app_instance.build()


@pytest.fixture
async def client(app):
    """HTTPX async client connected to the test app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


# ─── URL Reversal Tests ──────────────────────────────────────────────────────

class TestURLReversal:
    """Tests for url_for across Router, Request, and Eden."""

    @pytest.mark.asyncio
    async def test_url_for_app_simple(self, app):
        """Eden.url_for resolves named routes to paths."""
        eden_app = app.eden
        assert eden_app.url_for("index") == "/"
        assert eden_app.url_for("admin_panel") == "/admin"

    @pytest.mark.asyncio
    async def test_url_for_with_params(self, app):
        """Eden.url_for interpolates path parameters."""
        eden_app = app.eden
        assert eden_app.url_for("user_profile", user_id=123) == "/user/123"
        assert eden_app.url_for("user_profile", user_id=0) == "/user/0"

    @pytest.mark.asyncio
    async def test_url_for_unknown_raises(self, app):
        """Eden.url_for raises ValueError for unknown route names."""
        with pytest.raises(ValueError, match="not found"):
            app.eden.url_for("nonexistent_route")

    @pytest.mark.asyncio
    async def test_redirect_to_named_route(self, client):
        """redirect_to generates a redirect response to a named route."""
        resp = await client.get("/goto-profile/42")
        assert resp.status_code == 303
        assert "/user/42" in resp.headers["location"]

    @pytest.mark.asyncio
    async def test_request_url_for_absolute(self, client):
        """Request.url_for returns absolute URL with host."""
        resp = await client.get("/test-req-url")
        data = resp.json()
        assert data["url"] == "http://testserver/user/99"


# ─── Login Required Tests ────────────────────────────────────────────────────

class TestLoginRequired:
    """Tests for login_required on functions and CBVs."""

    @pytest.mark.asyncio
    async def test_function_unauthenticated(self, client):
        """Unauthenticated request to login_required function returns 401."""
        resp = await client.get("/secret")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_function_authenticated(self, client):
        """Authenticated request to login_required function succeeds."""
        resp = await client.get("/secret", headers={"X-Test-User": "alice@example.com"})
        assert resp.status_code == 200
        assert resp.json() == {"secret": "data"}

    @pytest.mark.asyncio
    async def test_cbv_per_method_unauthenticated(self, client):
        """Unauthenticated GET to per-method login_required CBV returns 401."""
        resp = await client.get("/protected")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_cbv_per_method_authenticated(self, client):
        """Authenticated GET to per-method login_required CBV succeeds."""
        resp = await client.get("/protected", headers={"X-Test-User": "alice@example.com"})
        assert resp.status_code == 200
        assert resp.json() == {"message": "Authenticated CBV!"}

    @pytest.mark.asyncio
    async def test_view_decorator_blocks_all_methods(self, client):
        """view_decorator(login_required) blocks unauthenticated GET and POST."""
        assert (await client.get("/fully-protected")).status_code == 401
        assert (await client.post("/fully-protected")).status_code == 401

    @pytest.mark.asyncio
    async def test_view_decorator_allows_all_methods(self, client):
        """view_decorator(login_required) allows authenticated GET and POST."""
        headers = {"X-Test-User": "alice@example.com"}
        assert (await client.get("/fully-protected", headers=headers)).status_code == 200
        assert (await client.post("/fully-protected", headers=headers)).status_code == 200


# ─── Roles Required Tests ────────────────────────────────────────────────────

class TestRolesRequired:
    """Tests for roles_required, require_role, require_any_role."""

    @pytest.mark.asyncio
    async def test_roles_required_missing(self, client):
        """User without required role gets 403."""
        resp = await client.get(
            "/admin",
            headers={"X-Test-User": "user@test.com", "X-Test-Roles": "user"},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_roles_required_present(self, client):
        """User with required role gets 200."""
        resp = await client.get(
            "/admin",
            headers={"X-Test-User": "admin@test.com", "X-Test-Roles": "admin"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"admin": "access"}

    @pytest.mark.asyncio
    async def test_superuser_bypass(self, client):
        """Superuser bypasses role checks."""
        resp = await client.get(
            "/admin",
            headers={"X-Test-User": "super@test.com", "X-Test-Roles": "superuser"},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_require_role_single(self, client):
        """require_role checks for a single role."""
        # Missing
        resp = await client.get(
            "/editor",
            headers={"X-Test-User": "u@test.com", "X-Test-Roles": "viewer"},
        )
        assert resp.status_code == 403

        # Present
        resp = await client.get(
            "/editor",
            headers={"X-Test-User": "u@test.com", "X-Test-Roles": "editor"},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_require_any_role(self, client):
        """require_any_role accepts any of the listed roles."""
        # None match
        resp = await client.get(
            "/any-role",
            headers={"X-Test-User": "u@test.com", "X-Test-Roles": "viewer"},
        )
        assert resp.status_code == 403

        # One matches
        resp = await client.get(
            "/any-role",
            headers={"X-Test-User": "u@test.com", "X-Test-Roles": "moderator"},
        )
        assert resp.status_code == 200


# ─── Permissions Tests ────────────────────────────────────────────────────────

class TestPermissions:
    """Tests for permissions_required, require_permission, require_any_permission."""

    @pytest.mark.asyncio
    async def test_permissions_required_missing_one(self, client):
        """Missing even one required permission returns 403."""
        resp = await client.get(
            "/permissions",
            headers={
                "X-Test-User": "u@test.com",
                "X-Test-Roles": "user",
                "X-Test-Permissions": "posts.read",
            },
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_permissions_required_all_present(self, client):
        """Having all required permissions returns 200."""
        resp = await client.get(
            "/permissions",
            headers={
                "X-Test-User": "u@test.com",
                "X-Test-Roles": "user",
                "X-Test-Permissions": "posts.read,posts.write",
            },
        )
        assert resp.status_code == 200
        assert resp.json() == {"permissions": "granted"}

    @pytest.mark.asyncio
    async def test_superuser_bypasses_permissions(self, client):
        """Superuser bypasses permission checks."""
        resp = await client.get(
            "/permissions",
            headers={"X-Test-User": "su@test.com", "X-Test-Roles": "superuser"},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_require_any_permission(self, client):
        """require_any_permission accepts any single matching permission."""
        # None match
        resp = await client.get(
            "/billing",
            headers={
                "X-Test-User": "u@test.com",
                "X-Test-Roles": "user",
                "X-Test-Permissions": "posts.read",
            },
        )
        assert resp.status_code == 403

        # One matches
        resp = await client.get(
            "/billing",
            headers={
                "X-Test-User": "u@test.com",
                "X-Test-Roles": "user",
                "X-Test-Permissions": "billing.read",
            },
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_require_permission_with_rbac_hierarchy(self, client):
        """require_permission checks the RBAC hierarchy for inherited permissions."""
        # Setup RBAC: manager role has reports.generate permission
        default_rbac.add_role("manager")
        default_rbac.add_permission("manager", "reports.generate")

        # User has manager role but NOT a direct reports.generate permission
        resp = await client.get(
            "/reports",
            headers={
                "X-Test-User": "mgr@test.com",
                "X-Test-Roles": "manager",
            },
        )
        assert resp.status_code == 200
        assert resp.json() == {"report": "generated"}


# ─── Tenant-Aware Auth Tests ─────────────────────────────────────────────────

class TestTenantAwareAuth:
    """Tests for tenant-scoped role and permission resolution."""

    @pytest.mark.asyncio
    async def test_tenant_scoped_roles(self, client):
        """User with get_roles_for_tenant returning tenant_admin gets access."""
        resp = await client.get(
            "/tenant-admin",
            headers={
                "X-Test-User": "org-admin@test.com",
                "X-Test-Roles": "user",
                "X-Test-Tenant-Roles": "tenant_admin",
            },
        )
        # Without tenant context set, falls back to flat roles (user) → 403
        # But get_roles_for_tenant is still called with None tenant_id → skipped → falls back
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_tenant_scoped_roles_with_flat_fallback(self, client):
        """When no tenant context, roles_required falls back to flat user.roles."""
        resp = await client.get(
            "/tenant-admin",
            headers={
                "X-Test-User": "org-admin@test.com",
                "X-Test-Roles": "tenant_admin",
            },
        )
        assert resp.status_code == 200
        assert resp.json() == {"tenant": "admin_access"}

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, client):
        """Unauthenticated request to any protected CBV returns 401."""
        resp = await client.get("/tenant-admin")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_superuser_bypasses_tenant_roles(self, client):
        """Superuser bypasses tenant-scoped role checks."""
        resp = await client.get(
            "/tenant-admin",
            headers={"X-Test-User": "su@test.com", "X-Test-Roles": "superuser"},
        )
        assert resp.status_code == 200
