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
        """
        if not self.schema_name:
            return

        from sqlalchemy import text
        from eden.db.base import Model
        from eden.db.session import get_db

        # Sanitize schema name
        safe_schema = "".join(c for c in self.schema_name if c.isalnum() or c == "_")
        
        # 1. Create the schema
        await session.execute(text(f"CREATE SCHEMA IF NOT EXISTS {safe_schema}"))
        
        # 2. Switch search_path to the new schema to ensure create_all targets it
        db_manager = get_db(None) # Helper doesn't need request if it's already in request.state or globally available
        # But wait, get_db takes 'request'. I can just call the method on the session's engine/manager if I have access.
        # Actually Model._db is stored.
        if hasattr(Model, "_db") and Model._db:
            await Model._db.set_schema(session, safe_schema)
            
            # 3. Create all tables in the new schema
            # We use the raw connection from the session to run sync create_all
            def _create_tables(conn):
                Model.metadata.create_all(bind=conn)
            
            await session.run_sync(_create_tables)
            
            # 4. Reset search_path (optional, but good practice)
            await Model._db.set_schema(session, None)

        await session.commit()


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
