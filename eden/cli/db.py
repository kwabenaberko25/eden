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
def db_init(db_url: str) -> None:
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
@click.option(
    "--db-url",
    default=None,
    help="Database URL (defaults to config).",
)
def db_migrate(db_url: str) -> None:
    """Apply pending migrations (alias for upgrade)."""
    click.echo("  ⬆️  Applying pending migrations...")
    run_upgrade(revision="head", db_url=db_url)
    click.echo("  ✅ Database migrated.")


@db.command("apply")
@click.option(
    "--db-url",
    default=None,
    help="Database URL (defaults to config).",
)
def db_apply(db_url: str) -> None:
    """Apply pending migrations (alias for migrate)."""
    db_migrate(db_url)


@db.command("upgrade")
@click.option("--revision", default="head", help="Target revision.")
@click.option(
    "--db-url",
    default=None,
    help="Database URL (defaults to config).",
)
def db_upgrade(revision: str, db_url: str) -> None:
    """Apply pending migrations."""
    click.echo(f"  ⬆️  Upgrading to: {revision}")
    run_upgrade(revision=revision, db_url=db_url)
    click.echo("  ✅ Database upgraded.")


@db.command("downgrade")
@click.option("--revision", default="-1", help="Target revision (default: -1).")
@click.option(
    "--db-url",
    default=None,
    help="Database URL (defaults to config).",
)
def db_downgrade(revision: str, db_url: str) -> None:
    """Revert to a previous migration."""
    click.echo(f"  ⬇️  Downgrading to: {revision}")
    run_downgrade(revision=revision, db_url=db_url)
    click.echo("  ✅ Database downgraded.")


@db.command("history")
@click.option(
    "--db-url",
    default=None,
    help="Database URL (defaults to config).",
)
def db_history(db_url: str) -> None:
    """Show migration history."""
    show_history(db_url=db_url)


@db.command("generate")
@click.option("-m", "--message", required=True, help="Migration message.")
@click.option(
    "--db-url",
    default=None,
    help="Database URL (defaults to config).",
)
def db_generate(message: str, db_url: str) -> None:
    """Generate a new database migration."""
    import alembic.util.exc

    click.echo(f"  🔄 Generating migration: {message}")
    try:
        create_migration(message=message, db_url=db_url)
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
