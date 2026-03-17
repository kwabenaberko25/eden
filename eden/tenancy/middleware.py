"""
Eden — Tenant Middleware

Resolves the current tenant from the request and sets it in context.
Supports multiple resolution strategies: subdomain, header, session, or path prefix.
"""

import logging
from typing import Any, Literal

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response as StarletteResponse

from eden.requests import Request
from eden.tenancy.context import reset_current_tenant, set_current_tenant
from eden.cache import InMemoryCache


def get_logger(name: str):
    """Get a logger instance."""
    return logging.getLogger(name)


class TenantMiddleware(BaseHTTPMiddleware):
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
        app: Any,
        *,
        strategy: Literal["subdomain", "header", "session", "path"] = "header",
        header_name: str = "X-Tenant-ID",
        session_key: str = "_tenant_id",
        base_domain: str = "",
        **kwargs,
    ) -> None:
        super().__init__(app, **kwargs)
        self.strategy = strategy
        self.header_name = header_name
        self.session_key = session_key
        self.base_domain = base_domain
        self._cache = InMemoryCache()

    def clear_tenant_cache(self) -> None:
        """Clear the tenant lookup cache. Call this when tenant data changes."""
        self._cache = InMemoryCache()  # Reset to new instance

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> StarletteResponse:
        """
        Main middleware dispatch that:
        1. Resolves the tenant from the request
        2. Sets tenant context for the request lifetime
        3. Ensures database session is available and switches schema if tenant uses dedicated schema
        4. Adds enforcement verification headers
        5. Resets context and schema after response
        
        Tenant Resolution Strategies:
        - subdomain: Extract from hostname (e.g., acme.myapp.com → acme)
        - header: Read from custom header (default: X-Tenant-ID)
        - session: Read tenant ID from session data
        - path: Extract from URL path prefix (e.g., /t/acme/...)
        
        Response Headers Added:
        - X-Tenant-Enforced: "true" if tenant context was active
        - X-Tenant-ID: The UUID of the enforced tenant (if applicable)
        """
        # Ensure database session is available
        if not hasattr(request.state, "db") or request.state.db is None:
            # Try to get from app state
            app = getattr(request, "app", None)
            if app and hasattr(app, "state") and hasattr(app.state, "db"):
                # Create a session from the database
                db = app.state.db
                session = await db.session().__aenter__()
                request.state.db = session
                # Set in context for QuerySet
                from eden.db.session import set_session
                request.state._db_token = set_session(session)
                request.state._db_cleanup = lambda: db.session().__aexit__(None, None, None)
            else:
                # No database configured, skip tenant schema switching
                pass

        tenant = await self._resolve_tenant(request)

        token = None
        tenant_id_str = None
        
        if tenant:
            # Set tenant context for this request
            token = set_current_tenant(tenant)
            request.state.tenant = tenant
            tenant_id_str = str(tenant.id)

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

        try:
            response = await call_next(request)
            
            # Add enforcement headers to response
            if tenant_id_str:
                response.headers["X-Tenant-Enforced"] = "true"
                response.headers["X-Tenant-ID"] = tenant_id_str
            
            return response
        finally:
            # Reset tenant context
            if token:
                reset_current_tenant(token)
                
            # Reset the PostgreSQL schema to public
            if hasattr(request.state, "tenant"):
                schema_name = getattr(request.state.tenant, "schema_name", None)
                if schema_name and hasattr(request.state, "db") and request.state.db:
                    db_session = request.state.db
                    try:
                        from eden.db import get_db
                        db_manager = get_db(request)
                        await db_manager.set_schema(db_session, "public")
                    except Exception:
                        pass  # Connection will be reused; log separately if needed
            
            # Clean up database session if we created it
            if hasattr(request.state, "_db_cleanup"):
                try:
                    await request.state._db_cleanup()
                except Exception:
                    pass
                if hasattr(request.state, "_db_token"):
                    from eden.db.session import reset_session
                    reset_session(request.state._db_token)

    async def _resolve_tenant(self, request: Request) -> Any | None:
        """Resolve the tenant based on the configured strategy."""
        tenant_identifier = None

        if self.strategy == "subdomain":
            tenant_identifier = self._extract_subdomain(request)
        elif self.strategy == "header":
            tenant_identifier = request.headers.get(self.header_name)
        elif self.strategy == "session":
            if hasattr(request, "session"):
                tenant_identifier = request.session.get(self.session_key)
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
        
        # Check cache first
        cached_tenant = await self._cache.get(cache_key)
        if cached_tenant is not None:
            return cached_tenant
        
        from sqlalchemy import select

        from eden.tenancy.models import Tenant

        session = getattr(request.state, "db", None)
        if not session:
            return None

        # Try by slug first, then by ID
        stmt = select(Tenant).where(
            (Tenant.slug == identifier) | (Tenant.id == identifier)
        ).where(Tenant.is_active)

        result = await session.execute(stmt)
        tenant = result.scalar_one_or_none()
        
        # Cache the result (even if None, to avoid repeated DB hits for invalid identifiers)
        await self._cache.set(cache_key, tenant, ttl=300)
        
        return tenant
