"""
Eden — Tenant Model

The base tenant/organization model for multi-tenant SaaS applications.
"""


from eden.db import Model, f, JSON


class Tenant(Model):
    """
    Base tenant (organization) model.

    Represents a single customer/organization in a multi-tenant SaaS system.
    Developers can extend this model or use it as-is.

    Usage:
        # Create a new tenant
        db = Tenant._get_db()
        async with db.transaction() as session:
            tenant = Tenant(name="Acme Corp", slug="acme-corp")
            session.add(tenant)

        # Look up by slug
        tenant = await Tenant.filter_one(slug="acme-corp")
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
    plan_id: str | None = f(foreign_key="eden_plans.id", nullable=True)

    # Optional PostgreSQL schema name for dedicated isolation
    schema_name: str | None = f(max_length=63, nullable=True)

    def __repr__(self) -> str:
        return f"<Tenant(name='{self.name}', slug='{self.slug}')>"

    async def save(self, session=None, *args, **kwargs):
        """Override save to trigger lifecycle events."""
        is_new = self.id is None
        was_active = True
        
        if not is_new:
            # Check old status if we wanted to be perfectly precise, but for now 
            # we check if it is being deactivated in this save.
            # A full implementation might load previous state from identity map.
            pass

        result = await super().save(session=session, *args, **kwargs)

        from eden.tenancy.signals import tenant_created, tenant_deactivated
        
        if is_new:
            await tenant_created.send(tenant=self)
        elif not self.is_active:
            # We trigger deactivated. Ideally we'd only trigger once when transitioning.
            await tenant_deactivated.send(tenant=self)
            
        return result

    async def delete(self, session=None, *args, **kwargs):
        """Override delete to trigger lifecycle events."""
        from eden.tenancy.signals import tenant_deleted
        await tenant_deleted.send(tenant=self)
        return await super().delete(session=session, *args, **kwargs)

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
            await session.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{safe_schema}"'))
            
            # 2. Save original search_path and switch to new schema
            result = await session.execute(text("SHOW search_path"))
            original_schema = result.scalar()
            
            # Set search_path to the new schema ONLY initially for table creation.
            # This prevents SQLAlchemy from thinking tables already exist if they are in 'public'.
            await session.execute(text(f'SET search_path TO "{safe_schema}"'))
            
            # 3. Create all framework tables in the new schema
            def _create_tables(sync_session):
                """Create all tables synchronously in the current schema."""
                Model.metadata.create_all(bind=sync_session.connection())
            
            await session.run_sync(_create_tables)
            
            # Now add public to the path for any subsequent operations (like extensions)
            await session.execute(text(f'SET search_path TO "{safe_schema}", public'))
            
            # 4. Stamp the schema with the current migration head inside this transaction
            # This ensures subsequent 'eden db migrate --schema X' calls work correctly
            # without requiring an external uncommitted connection.
            from eden.db.migrations import MigrationManager
            from alembic.script import ScriptDirectory
            
            manager = MigrationManager()
            script = ScriptDirectory.from_config(manager.config)
            head_rev = script.get_current_head()
            
            if head_rev:
                # Create the Alembic version table explicitly for the tenant
                await session.execute(text(f'''
                    CREATE TABLE IF NOT EXISTS "{safe_schema}".alembic_version_tenant (
                        version_num VARCHAR(32) NOT NULL, 
                        CONSTRAINT alembic_version_tenant_pkc PRIMARY KEY (version_num)
                    )
                '''))
                # Insert the head revision
                await session.execute(text(
                    f'INSERT INTO "{safe_schema}".alembic_version_tenant (version_num) VALUES (:head)'
                ), {"head": head_rev})
            
            # 5. Commit the schema creation and table setup
            # (Note: Caller will typically commit the overall transaction)
            
            from eden.tenancy.signals import tenant_schema_provisioned
            await tenant_schema_provisioned.send(tenant=self, session=session)
            
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
                    except Exception as e:
                        from eden.logging import get_logger
                        get_logger(__name__).error("Silent exception caught: %s", e, exc_info=True)  # If this fails too, let exception from main block propagate


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


class Plan(Model):
    """
    Tier/Plan definition for SaaS applications.
    
    Tablename: eden_plans
    """
    __tablename__ = "eden_plans"

    name: str = f(max_length=100, unique=True)
    slug: str = f(max_length=50, unique=True, index=True)
    description: str | None = f(nullable=True)
    is_active: bool = f(default=True)
    features: dict = f(type_=JSON, default=dict) # JSON list of features/limits
    
    # Metadata for billing sync
    sync_metadata: dict = f(type_=JSON, default=dict)

    def __repr__(self) -> str:
        return f"<Plan(name='{self.name}')>"


class Price(Model):
    """
    Pricing tiers for Plans. Supports multi-currency and intervals.
    
    Tablename: eden_prices
    """
    __tablename__ = "eden_prices"

    plan_id: str = f(foreign_key="eden_plans.id", index=True)
    currency: str = f(max_length=3, default="USD")
    amount: int = f(default=0) # In cents
    interval: str = f(max_length=20, default="month") # month, year, etc.
    is_active: bool = f(default=True)
    
    # Sync fields for external providers (Stripe, etc.)
    provider_price_id: str | None = f(max_length=255, nullable=True, unique=True)

    def __repr__(self) -> str:
        return f"<Price(amount={self.amount}, currency='{self.currency}', interval='{self.interval}')>"
