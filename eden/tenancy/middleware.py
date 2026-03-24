"""
Eden — Tenant Middleware

Resolves the current tenant from the request and sets it in context.
Supports multiple resolution strategies: subdomain, header, session, or path prefix.
"""

import logging
from typing import Any, Literal, Optional

from starlette.types import ASGIApp, Receive, Scope, Send, Message

from eden.requests import Request
from eden.tenancy.context import reset_current_tenant, set_current_tenant
from eden.cache import InMemoryCache


def get_logger(name: str):
    """Get a logger instance."""
    return logging.getLogger(name)


class TenantMiddleware:
    """
    Middleware that resolves the current tenant from the request
    and stores it in a ContextVar for the duration of the request.

    Strategies:
        - "subdomain": Extracts tenant slug from the subdomain (e.g., acme.myapp.com)
        - "header": Reads tenant ID or slug from a custom header (default: X-Tenant-ID)
        - "session": Reads tenant ID from the session
        - "path": Extracts tenant slug from the URL path prefix (e.g., /t/acme/...)

    Usage:
        app.add_middleware("tenant", strategy="subdomain")
        # or
        app.add_middleware("tenant", strategy="header", header_name="X-Tenant-ID")
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        strategy: Literal["subdomain", "header", "session", "path"] = "header",
        header_name: str = "X-Tenant-ID",
        session_key: str = "_tenant_id",
        base_domain: str = "",
        **kwargs,
    ) -> None:
        self.app = app
        self.strategy = strategy
        self.header_name = header_name
        self.session_key = session_key
        self.base_domain = base_domain
        self._fallback_cache = InMemoryCache(max_size=5000)

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        """Compatibility wrapper for tests calling .dispatch directly."""
        # 1. Ensure database session is available in request state
        db_cleanup = None
        db_token = None
        
        if not hasattr(request.state, "db") or request.state.db is None:
            # Try to get from app state
            app_instance = request.scope.get("app")
            eden_app = getattr(app_instance, "eden", None)
            if eden_app and hasattr(eden_app, "state") and hasattr(eden_app.state, "db"):
                db = eden_app.state.db
                ctx_manager = db.session()
                session = await ctx_manager.__aenter__()
                request.state.db = session
                
                # Set in context for QuerySet
                from eden.db.session import set_session
                db_token = set_session(session)
                
                async def cleanup():
                    await ctx_manager.__aexit__(None, None, None)
                db_cleanup = cleanup

        # 2. Resolve Tenant
        tenant = await self._resolve_tenant(request)

        token = None
        tenant_id_str = None
        
        if tenant:
            # Set tenant context for this request
            token = set_current_tenant(tenant)
            request.state.tenant = tenant
            tenant_id_str = str(tenant.id)
            
            from eden.context import get_request_id
            rid = get_request_id()
            get_logger(__name__).debug(f"[{rid}] Enforcing tenant: {tenant.slug} ({tenant_id_str})")

            # Set DB session variable for Postgres RLS if session exists
            if hasattr(request.state, "db") and request.state.db:
                from sqlalchemy import text
                try:
                    await request.state.db.execute(
                        text("SELECT set_config('app.current_tenant_id', :tid, true)"),
                        {"tid": tenant_id_str}
                    )
                except Exception as e:
                    get_logger(__name__).warning(f"Failed to set tenant session variable: {e}")

            # If the tenant has a dedicated schema, switch to it
            schema_name = getattr(tenant, "schema_name", None)
            if schema_name and hasattr(request.state, "db") and request.state.db:
                db_session = request.state.db
                from eden.db import get_db
                try:
                    db_manager = get_db(request)
                    await db_manager.set_schema(db_session, schema_name)
                except Exception as e:
                    get_logger(__name__).warning(f"Failed to switch to tenant schema {schema_name}: {e}")

        # 3. Proceed
        try:
            response = await call_next(request)
            
            # Inject headers
            if tenant_id_str:
                response.headers["x-tenant-enforced"] = "true"
                response.headers["x-tenant-id"] = tenant_id_str
                
            return response
        finally:
            # 5. Cleanup
            if token:
                reset_current_tenant(token)
                
            # Reset the PostgreSQL schema to public
            if hasattr(request.state, "tenant"):
                tenant_obj = request.state.tenant
                schema_name = getattr(tenant_obj, "schema_name", None)
                if schema_name and hasattr(request.state, "db") and request.state.db:
                    db_session = request.state.db
                    try:
                        from eden.db import get_db
                        db_manager = get_db(request)
                        await db_manager.set_schema(db_session, "public")
                    except Exception:
                        pass
            
            # Clean up database session
            if db_cleanup:
                try:
                    await db_cleanup()
                except Exception:
                    pass
            if db_token:
                from eden.db.session import reset_session
                reset_session(db_token)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Pure ASGI implementation of tenant resolution.
        
        1. Resolves the tenant from the request
        2. Sets tenant context for the request lifetime
        3. Ensures database session is available and switches schema if tenant uses dedicated schema
        4. Adds enforcement verification headers to response
        5. Resets context and schema after response
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        
        # 1. Ensure database session is available in request state
        # (This logic is moved from the original dispatch to ensure DB-backed tenant lookup works)
        db_cleanup = None
        db_token = None
        
        if not hasattr(request.state, "db") or request.state.db is None:
            # Try to get from app state
            app_instance = scope.get("app")
            # In Eden, the app is attached to the Starlette app
            eden_app = getattr(app_instance, "eden", None)
            if eden_app and hasattr(eden_app, "state") and hasattr(eden_app.state, "db"):
                db = eden_app.state.db
                ctx_manager = db.session()
                session = await ctx_manager.__aenter__()
                request.state.db = session
                
                # Set in context for QuerySet
                from eden.db.session import set_session
                db_token = set_session(session)
                
                async def cleanup():
                    await ctx_manager.__aexit__(None, None, None)
                db_cleanup = cleanup

        # 2. Resolve Tenant
        tenant = await self._resolve_tenant(request)

        token = None
        tenant_id_str = None
        
        if tenant:
            # Set tenant context for this request
            token = set_current_tenant(tenant)
            request.state.tenant = tenant
            tenant_id_str = str(tenant.id)
            
            from eden.context import get_request_id
            rid = get_request_id()
            get_logger(__name__).debug(f"[{rid}] Enforcing tenant: {tenant.slug} ({tenant_id_str})")

            # Set DB session variable for Postgres RLS if session exists
            if hasattr(request.state, "db") and request.state.db:
                from sqlalchemy import text
                try:
                    # Use SET LOCAL to ensure it's scoped and cleared on transaction end/rollback
                    await request.state.db.execute(
                        text("SELECT set_config('app.current_tenant_id', :tid, true)"),
                        {"tid": tenant_id_str}
                    )
                except Exception as e:
                    get_logger(__name__).warning(f"Failed to set tenant session variable: {e}")

            # If the tenant has a dedicated schema, switch to it
            schema_name = getattr(tenant, "schema_name", None)
            if schema_name and hasattr(request.state, "db") and request.state.db:
                db_session = request.state.db
                from eden.db import get_db
                try:
                    db_manager = get_db(request)
                    await db_manager.set_schema(db_session, schema_name)
                except Exception as e:
                    logger = get_logger(__name__)
                    logger.warning(f"Failed to switch to tenant schema {schema_name}: {e}")

        # 3. Create a wrapper for 'send' to inject headers
        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start" and tenant_id_str:
                headers = list(message.get("headers", []))
                headers.append((b"x-tenant-enforced", b"true"))
                headers.append((b"x-tenant-id", tenant_id_str.encode()))
                message["headers"] = headers
            await send(message)

        # 4. Execute the application stack
        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            # 5. Cleanup
            if token:
                reset_current_tenant(token)
                
            # Reset the PostgreSQL schema to public
            if hasattr(request.state, "tenant"):
                tenant_obj = request.state.tenant
                schema_name = getattr(tenant_obj, "schema_name", None)
                if schema_name and hasattr(request.state, "db") and request.state.db:
                    db_session = request.state.db
                    try:
                        from eden.db import get_db
                        db_manager = get_db(request)
                        await db_manager.set_schema(db_session, "public")
                    except Exception:
                        pass
            
            # Clean up database session
            if db_cleanup:
                try:
                    await db_cleanup()
                except Exception:
                    pass
            if db_token:
                from eden.db.session import reset_session
                reset_session(db_token)

    async def _resolve_tenant(self, request: Request) -> Any | None:
        """Resolve the tenant based on the configured strategy."""
        tenant_identifier = None

        if self.strategy == "subdomain":
            tenant_identifier = self._extract_subdomain(request)
        elif self.strategy == "header":
            tenant_identifier = request.headers.get(self.header_name)
        elif self.strategy == "session":
            if "session" in request.scope:
                tenant_identifier = request.scope["session"].get(self.session_key)
        elif self.strategy == "path":
            tenant_identifier = self._extract_path_prefix(request)

        if not tenant_identifier:
            return None

        return await self._fetch_tenant(tenant_identifier, request)

    def _extract_subdomain(self, request: Request) -> str | None:
        """Extract tenant slug from subdomain."""
        host = request.headers.get("host", "")
        if not self.base_domain or self.base_domain not in host:
            return None

        subdomain = host.replace(f".{self.base_domain}", "").split(":")[0]
        if subdomain and subdomain != "www":
            return subdomain
        return None

    def _extract_path_prefix(self, request: Request) -> str | None:
        """Extract tenant slug from URL path prefix (e.g., /t/acme/...)."""
        parts = request.url.path.strip("/").split("/")
        if len(parts) >= 2 and parts[0] == "t":
            return parts[1]
        return None

    async def _fetch_tenant(self, identifier: str, request: Request) -> Any | None:
        """Look up the tenant by slug or ID, with caching."""
        cache_key = f"tenant:{identifier}"
        
        # Use app's global cache if available for distributed consistency
        # Access eden_app.cache
        app_instance = request.scope.get("app")
        eden_app = getattr(app_instance, "eden", None)
        cache = getattr(eden_app, "cache", self._fallback_cache)
        
        if hasattr(cache, "global_cache"):
            # We use global_cache to store tenants so they are shared across all processes
            cache = cache.global_cache
        
        # Check cache first
        cached_tenant = await cache.get(cache_key)
        if cached_tenant is not None:
            return cached_tenant
        
        from sqlalchemy import select
        from eden.tenancy.models import Tenant

        session = getattr(request.state, "db", None)
        if not session:
            return None

        # Try by slug first, then by ID (validate UUID format to prevent server crashes)
        import uuid as uuid_mod
        try:
            # Check if identifier is a valid UUID
            uuid_val = uuid_mod.UUID(identifier)
            stmt = select(Tenant).where(
                (Tenant.slug == identifier) | (Tenant.id == uuid_val)
            )
        except (ValueError, TypeError):
            # Not a UUID, only query by slug
            stmt = select(Tenant).where(Tenant.slug == identifier)

        stmt = stmt.where(Tenant.is_active)

        result = await session.execute(stmt)
        tenant = result.scalar_one_or_none()
        
        # Cache only successful lookups. Negative results (None) are NOT cached
        # to avoid making newly created tenants invisible during the TTL window.
        if tenant is not None:
            await cache.set(cache_key, tenant, ttl=300)
        
        return tenant
