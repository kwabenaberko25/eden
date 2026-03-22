"""
Eden DB — CLI database migration utilities.
"""

from __future__ import annotations

import sys
import click
from eden.db.migrations import (
    init_migrations,
    create_migration,
    run_upgrade,
    run_downgrade,
    show_history,
    run_check,
    MigrationManager,
)


@click.group(name="db")
def db() -> None:
    """🗄️  Eden Database — Initialize, generate, and run migrations."""
    pass


@db.command("init")
@click.option(
    "--db-url",
    default=None,
    help="Database URL (defaults to config).",
)
def db_init(db_url: str | None) -> None:
    """Initialize the migrations directory."""
    try:
        init_migrations(db_url=db_url)
        click.echo("  ✅ Migrations directory created.")
        click.echo("  📁 migrations/")
        click.echo("  📄 alembic.ini")
        click.echo("  💡 Next Steps:")
        click.echo("     1. Import your models in migrations/env.py (if not using core models).")
        click.echo("     2. Run 'eden db generate -m \"initial\"' to create your first migration.")
        click.echo("     3. Run 'eden db migrate' to apply it.")
    except FileExistsError:
        click.echo("  ❌ Migrations directory already exists.", err=True)
        sys.exit(1)


@db.command("migrate")
@click.option("--revision", default="head", help="Target revision.")
@click.option("--schema", default=None, help="Target specific tenant schema.")
@click.option("--all-tenants", is_flag=True, help="Apply migrations to ALL active tenant schemas.")
@click.option(
    "--db-url",
    default=None,
    help="Database URL (defaults to config).",
)
def db_migrate(revision: str, schema: str | None, all_tenants: bool, db_url: str | None) -> None:
    """Apply pending migrations."""
    if schema and all_tenants:
        click.echo("  ❌ Error: Cannot use both --schema and --all-tenants.", err=True)
        sys.exit(1)

    if all_tenants:
        click.echo(f"  ⬆️  Applying migrations to {revision} on ALL tenants...")
        run_upgrade(revision=revision, db_url=db_url, all_tenants=True)
    else:
        target = f"schema '{schema}'" if schema else "default schema"
        click.echo(f"  ⬆️  Applying migrations to {revision} on {target}...")
        run_upgrade(revision=revision, db_url=db_url, schema=schema)
    
    click.echo("  ✅ Database migrated.")


@db.command("apply")
@click.option("--revision", default="head", help="Target revision.")
@click.option("--schema", default=None, help="Target specific tenant schema.")
@click.option("--all-tenants", is_flag=True, help="Apply migrations to ALL active tenant schemas.")
@click.option(
    "--db-url",
    default=None,
    help="Database URL (defaults to config).",
)
def db_apply(revision: str, schema: str | None, all_tenants: bool, db_url: str | None) -> None:
    """Apply pending migrations (alias for migrate)."""
    db_migrate(revision=revision, schema=schema, all_tenants=all_tenants, db_url=db_url)


@db.command("upgrade")
@click.option("--revision", default="head", help="Target revision.")
@click.option("--schema", default=None, help="Target specific tenant schema.")
@click.option("--all-tenants", is_flag=True, help="Apply migrations to ALL active tenant schemas.")
@click.option(
    "--db-url",
    default=None,
    help="Database URL (defaults to config).",
)
def db_upgrade(revision: str, schema: str | None, all_tenants: bool, db_url: str | None) -> None:
    """Apply pending migrations."""
    db_migrate(revision=revision, schema=schema, all_tenants=all_tenants, db_url=db_url)


@db.command("downgrade")
@click.option("--revision", default="-1", help="Target revision (default: -1).")
@click.option("--schema", default=None, help="Target specific tenant schema.")
@click.option(
    "--db-url",
    default=None,
    help="Database URL (defaults to config).",
)
def db_downgrade(revision: str, schema: str | None, db_url: str | None) -> None:
    """Revert to a previous migration."""
    target = f"schema '{schema}'" if schema else "default schema"
    click.echo(f"  ⬇️  Downgrading to: {revision} on {target}")
    run_downgrade(revision=revision, db_url=db_url, schema=schema)
    click.echo("  ✅ Database downgraded.")


@db.command("history")
@click.option(
    "--db-url",
    default=None,
    help="Database URL (defaults to config).",
)
def db_history(db_url: str) -> None:
    """Show migration history intelligently."""
    click.echo("  📜 Migration History:")
    from eden.db.migrations import MigrationManager
    
    manager = MigrationManager(db_url)
    history_data = manager.history()
    
    if not history_data:
        click.echo("     (No migrations found)")
        return
        
    for item in history_data:
        status_color = "green" if item["status"] == "applied" else "yellow"
        status_icon = "✅" if item["status"] == "applied" else "⏳"
        
        flags = []
        if item["is_head"]:
            flags.append("HEAD")
        if item["is_current"]:
            flags.append("CURRENT")
            
        flag_str = f" [{', '.join(flags)}]" if flags else ""
        
        click.secho(
            f"  {status_icon} {item['revision']} - {item['message']}{flag_str}",
            fg=status_color
        )


@db.command("generate")
@click.option("-m", "--message", required=True, help="Migration message.")
@click.option("--tenant", is_flag=True, help="Generate migration for tenant-isolated models.")
@click.option(
    "--db-url",
    default=None,
    help="Database URL (defaults to config).",
)
def db_generate(message: str, tenant: bool, db_url: str | None) -> None:
    """Generate a new database migration."""
    import alembic.util.exc

    label = "Tenant" if tenant else "Shared"
    click.echo(f"  🔄 Generating {label} migration: {message}")
    try:
        manager = MigrationManager(db_url)
        manager.generate(message=message, tenant_isolated=tenant)
        click.echo("  ✅ Migration created in migrations/versions/")
    except alembic.util.exc.CommandError as e:
        if "Path doesn't exist" in str(e):
            click.echo("  ❌ Error: Migrations directory not found.", err=True)
            click.echo("  💡 Run 'eden db init' first to initialize migrations.", err=True)
        else:
            click.echo(f"  ❌ Error: {e}", err=True)
        sys.exit(1)


@db.command("check")
@click.option(
    "--db-url",
    default=None,
    help="Database URL (defaults to config).",
)
def db_check(db_url: str) -> None:
    """Check for schema drift across all tenants."""
    click.echo("  🕵️  Checking for schema drift...")
    results = run_check(db_url=db_url)
    
    any_drift = False
    for schema, status in results.items():
        if status == "ok":
            click.echo(f"  ✅ {schema}: OK")
        else:
            any_drift = True
            click.echo(f"  ❌ {schema}: {status}")

@db.command("provision-tenants")
@click.option(
    "--db-url",
    default=None,
    help="Database URL (defaults to config).",
)
def db_provision_tenants(db_url: str) -> None:
    """Provision schemas for all tenants that need them."""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy import select
    from eden.tenancy.models import Tenant
    from eden.config import get_db_url
    import asyncio

    async def provision():
        url = db_url or get_db_url()
        engine = create_async_engine(url)
        
        async with AsyncSession(engine) as session:
            # Get all tenants with schema_name set
            stmt = select(Tenant).where(Tenant.schema_name.isnot(None), Tenant.is_active)
            result = await session.execute(stmt)
            tenants = result.scalars().all()
            
            if not tenants:
                click.echo("  ℹ️  No tenants found with schema_name set.")
                return
            
            click.echo(f"  🔍 Found {len(tenants)} tenant(s) to provision.")
            
            for tenant in tenants:
                click.echo(f"  🏗️  Provisioning schema for tenant '{tenant.name}' ({tenant.schema_name})...")
                try:
                    await tenant.provision_schema(session)
                    click.echo(f"  ✅ Schema '{tenant.schema_name}' provisioned.")
                except Exception as e:
                    click.echo(f"  ❌ Failed to provision schema for '{tenant.name}': {e}", err=True)
                    continue
            
            click.echo("  ✨ Tenant provisioning complete.")

    asyncio.run(provision())
