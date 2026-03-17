"""
Eden — Tenant Model

The base tenant/organization model for multi-tenant SaaS applications.
"""


from eden.db import Model, f


class Tenant(Model):
    """
    Base tenant (organization) model.

    Represents a single customer/organization in a multi-tenant SaaS system.
    Developers can extend this model or use it as-is.

    Usage:
        # Create a new tenant
        tenant = Tenant(name="Acme Corp", slug="acme-corp")
        session.add(tenant)
        await session.commit()

        # Look up by slug
        tenant = await Tenant.filter_one(session, slug="acme-corp")
    """

    __tablename__ = "eden_tenants"

    # Organization name
    name: str = f(max_length=255)

    # URL-safe slug for subdomain routing (e.g., "acme-corp")
    slug: str = f(max_length=100, unique=True, index=True)

    # Soft-disable without deleting
    is_active: bool = f(default=True)

    # Optional plan/tier identifier
    plan: str | None = f(max_length=50, nullable=True)

    # Optional PostgreSQL schema name for dedicated isolation
    schema_name: str | None = f(max_length=63, nullable=True)

    def __repr__(self) -> str:
        return f"<Tenant(name='{self.name}', slug='{self.slug}')>"

    async def provision_schema(self, session) -> None:
        """
        Dynamically creates the PostgreSQL schema for this tenant
        and provisions all framework tables within it.
        
        This method:
        1. Creates a new schema with safe naming
        2. Switches to that schema within the transaction
        3. Creates all framework tables in that schema
        4. Resets to public schema to prevent connection pool issues
        
        Args:
            session: AsyncSession instance (typically from a request context or explicit binding)
        
        Raises:
            ValueError: If schema_name is not set on this tenant
            Exception: If schema creation or table provisioning fails
        
        Implementation Notes:
            - Transaction is auto-committed by the caller
            - Must reset schema_path after provisioning to prevent connection pool leaks
            - Uses session.run_sync() for sync metadata.create_all()
        """
        if not self.schema_name:
            raise ValueError("Tenant.provision_schema() requires schema_name to be set")

        from sqlalchemy import text
        from eden.db import Model

        # Sanitize schema name: alphanumeric + underscore only
        # PostgreSQL limits identifiers to 63 bytes, but we're being conservative
        safe_schema = "".join(c for c in self.schema_name if c.isalnum() or c == "_")
        if not safe_schema:
            raise ValueError(f"Schema name '{self.schema_name}' contains no valid characters")

        original_schema = None
        try:
            # 1. Create the schema if it doesn't exist
            await session.execute(text(f"CREATE SCHEMA IF NOT EXISTS {safe_schema}"))
            
            # 2. Save original search_path and switch to new schema
            # This ensures all CREATE TABLE commands target the new schema
            result = await session.execute(text("SHOW search_path"))
            original_schema = result.scalar()
            
            # Set search_path to the new schema first, then public (for extensions)
            await session.execute(text(f"SET search_path TO {safe_schema}, public"))
            
            # 3. Create all framework tables in the new schema
            # Using run_sync to execute the synchronous metadata.create_all()
            def _create_tables(sync_session):
                """Create all tables synchronously in the current schema."""
                Model.metadata.create_all(bind=sync_session.connection())
            
            await session.run_sync(_create_tables)
            
            # 4. Commit the schema creation and table setup
            # (Note: Caller will typically commit the overall transaction)
            
        finally:
            # CRITICAL: Always reset search_path to prevent connection pool issues
            # If a connection with wrong search_path is returned to the pool,
            # subsequent connections will inherit it, causing data isolation violations
            if original_schema is not None:
                try:
                    await session.execute(text(f"SET search_path TO {original_schema}"))
                except Exception:
                    # Even if reset fails, we try to at least set it to safe default
                    try:
                        await session.execute(text("SET search_path TO public"))
                    except Exception:
                        pass  # If this fails too, let exception from main block propagate


class AnonymousTenant:
    """
    A null-object implementation of the Tenant model.
    Used when no tenant is resolved (e.g., in non-tenant projects).
    """

    id = None
    name = "Global"
    slug = None
    is_active = True
    plan = "premium"
    schema_name = None

    def __repr__(self) -> str:
        return "<AnonymousTenant>"
