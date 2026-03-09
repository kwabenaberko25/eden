import os
import logging
from typing import Any, Optional
from alembic import command
from alembic.config import Config

logger = logging.getLogger("eden.migrations")


class MigrationManager:
    """
    MigrationManager: Eden's database migration engine.
    Handles schema evolution using Alembic under the hood.
    """

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.config = self._get_alembic_config()

    def _get_alembic_config(self) -> Config:
        """Initialize Alembic configuration."""
        # Check for alembic.ini in current directory or app root
        ini_path = "alembic.ini"
        if not os.path.exists(ini_path):
            # Fallback to a default location or error
            logger.warning("alembic.ini not found. Using default config.")

        cfg = Config(ini_path)
        cfg.set_main_option("sqlalchemy.url", self.database_url)
        # Ensure script_location is set (usually 'migrations')
        if not cfg.get_main_option("script_location"):
            cfg.set_main_option("script_location", "migrations")
        return cfg

    async def init(self) -> None:
        """Initialize migration directory."""
        logger.info("Migrations: Initializing environment...")
        script_location = self.config.get_main_option("script_location")
        if os.path.exists(script_location):
            logger.warning(
                f"Migrations: Directory '{script_location}' already exists."
            )
            return

        command.init(self.config, script_location, template="generic")
        logger.info(f"Migrations: Environment created at '{script_location}'.")

    async def generate(self, message: str, tenant_isolated: bool = False) -> None:
        """
        Detect schema changes and generate a new migration file.
        
        If tenant_isolated=True, it identifies changes in models marked with __eden_tenant_isolated__=True.
        """
        label = "Tenant" if tenant_isolated else "Shared"
        logger.info(f"Migrations: Generating {label} revision — '{message}'")
        
        # Configure the environment with isolation context
        opts = {
            "autogenerate": True,
            "version_table": "alembic_version_tenant" if tenant_isolated else "alembic_version",
            # This will be picked up by the env.py to filter metadata
            "include_object": self._make_include_object(tenant_isolated)
        }
        
        try:
            command.revision(self.config, message=message, **opts)
            logger.info(f"Migrations: {label} revision successfully generated.")
        except Exception as e:
            logger.error(f"Migration Error: {e}")
            raise

    async def migrate(self, revision: str = "head", schema: Optional[str] = None) -> None:
        """
        Apply pending migrations to the database.
        
        If schema is provided, it applies migrations specifically to that tenant schema.
        """
        target = f"schema '{schema}'" if schema else "default schema"
        logger.info(f"Migrations: Applying evolutions to {revision} on {target}...")
        
        config = self._get_alembic_config()
        if schema:
            # Tell Alembic to use a specific schema and target the tenant-specific version table
            config.set_main_option("tenant_schema", schema)
        
        try:
            command.upgrade(config, revision)
            logger.info(f"Migrations: {target} is now up-to-date.")
        except Exception as e:
            logger.error(f"Migration Error: {e}")
            raise

    def _make_include_object(self, tenant_isolated: bool):
        """Returns a filter function for Alembic auto-generation."""
        def include_object(obj, name, type_, reflected, compare_to):
            if type_ == "table":
                # Get the model associated with this table
                # NOTE: This assumes models are already loaded in metadata
                from eden.db import Model
                model = None
                for mapper in Model.registry.mappers:
                    if mapper.persist_selectable.name == name:
                        model = mapper.class_
                        break
                
                if model:
                    is_isolated = getattr(model, "__eden_tenant_isolated__", False)
                    return is_isolated == tenant_isolated
                
                # If no model found, default to shared if not explicitly isolation-requested
                return not tenant_isolated
            return True
        return include_object

    async def check(self) -> dict[str, str]:
        """
        Check for schema drift across all tenants.
        Returns a dictionary mapping schema names to their drift status (or "ok").
        """
        from alembic.script import ScriptDirectory
        from sqlalchemy import text, select
        from eden.db import Model
        from eden.tenancy.models import Tenant

        logger.info("Migrations: Checking for schema drift...")
        script = ScriptDirectory.from_config(self.config)
        head_revision = script.get_current_head()
        
        results = {}

        # 1. Check shared schema
        async with Model._get_db().session() as sess:
            res = await sess.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
            shared_version = res.scalar()
            results["shared"] = "ok" if shared_version == head_revision else f"drifted (expected {head_revision}, got {shared_version})"

            # 2. Get all tenants
            # Note: We use Model.query because Tenant is an EdenModel
            tenants = await sess.execute(select(Tenant))
            tenant_list = tenants.scalars().all()

            for tenant in tenant_list:
                schema = tenant.schema_name
                try:
                    # Check tenant version table
                    version_sql = text(f'SELECT version_num FROM "{schema}".alembic_version_tenant LIMIT 1')
                    res = await sess.execute(version_sql)
                    tenant_version = res.scalar()
                    
                    if tenant_version == head_revision:
                        results[schema] = "ok"
                    else:
                        results[schema] = f"drifted (expected {head_revision}, got {tenant_version})"
                except Exception as e:
                    results[schema] = f"error: {str(e)}"

        return results

    async def downgrade(self, revision: str) -> None:
        """Revert to a previous migration."""
        logger.info(f"Migrations: Reverting to {revision}...")
        try:
            command.downgrade(self.config, revision)
            logger.info("Migrations: Schema reverted.")
        except Exception as e:
            logger.error(f"Migration Error: {e}")
            raise

    def history(self) -> None:
        """Show migration history."""
        command.history(self.config)


# ── Functional Interface ──────────────────────────────────────────────────

def init_migrations(db_url: str):
    import asyncio
    manager = MigrationManager(db_url)
    asyncio.run(manager.init())


def create_migration(message: str, db_url: str):
    import asyncio
    manager = MigrationManager(db_url)
    asyncio.run(manager.generate(message))


def run_upgrade(revision: str, db_url: str):
    import asyncio
    manager = MigrationManager(db_url)
    asyncio.run(manager.migrate(revision))


def run_downgrade(revision: str, db_url: str):
    import asyncio
    manager = MigrationManager(db_url)
    asyncio.run(manager.downgrade(revision))


def show_history(db_url: str):
    manager = MigrationManager(db_url)
    manager.history()


def run_check(db_url: str) -> dict[str, str]:
    import asyncio
    manager = MigrationManager(db_url)
    return asyncio.run(manager.check())
