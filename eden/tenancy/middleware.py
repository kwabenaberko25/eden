"""
Eden — Tenant Middleware

Resolves the current tenant from the request and sets it in context.
Supports multiple resolution strategies: subdomain, header, session, or path prefix.
"""

from typing import Any, Literal

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response as StarletteResponse

from eden.requests import Request
from eden.tenancy.context import reset_current_tenant, set_current_tenant


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

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> StarletteResponse:
        tenant = await self._resolve_tenant(request)

        token = None
        if tenant:
            token = set_current_tenant(tenant)
            request.state.tenant = tenant

            # If the tenant has a dedicated schema, switch to it
            schema_name = getattr(tenant, "schema_name", None)
            if schema_name:
                db_session = getattr(request.state, "db", None)
                if db_session:
                    from eden.orm import get_db
                    db_manager = get_db(request)
                    await db_manager.set_schema(db_session, schema_name)

        try:
            response = await call_next(request)
            return response
        finally:
            if token:
                reset_current_tenant(token)
                
            # CRITICAL: Always reset the PostgreSQL schema to public to prevent connection pool leaks
            # where a connection is returned to the pool with the wrong search_path.
            schema_name = getattr(request.state.tenant, "schema_name", None) if getattr(request.state, "tenant", None) else None
            if schema_name:
                db_session = getattr(request.state, "db", None)
                if db_session:
                    try:
                        from eden.orm import get_db
                        db_manager = get_db(request)
                        await db_manager.set_schema(db_session, "public")
                    except Exception:
                        pass

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
        """Look up the tenant by slug or ID."""
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
        return result.scalar_one_or_none()
