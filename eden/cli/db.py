"""
Eden DB — CLI database migration utilities.
"""

from __future__ import annotations

import asyncio
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


def _execute_migration(revision: str, schema: str | None, all_tenants: bool, db_url: str | None) -> None:
    """Helper to execute migration logic."""
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
    _execute_migration(revision=revision, schema=schema, all_tenants=all_tenants, db_url=db_url)


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
    _execute_migration(revision=revision, schema=schema, all_tenants=all_tenants, db_url=db_url)


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
    _execute_migration(revision=revision, schema=schema, all_tenants=all_tenants, db_url=db_url)


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
def db_history(db_url: str | None) -> None:
    """Show migration history with a premium overview."""
    from rich.console import Console
    from rich.table import Table
    
    console = Console()
    manager = MigrationManager(db_url)
    history_data = asyncio.run(manager.history())
    
    if not history_data:
        click.secho("  ℹ (No migrations found)", fg="yellow")
        return
        
    table = Table(title="📜 Eden Migration History", show_header=True, header_style="bold magenta")
    table.add_column("Status", justify="center")
    table.add_column("Revision", style="dim")
    table.add_column("Message", width=60)
    table.add_column("Markers", justify="right")
    
    for item in history_data:
        is_applied = item["status"] == "applied"
        status_icon = "[green]✅[/]" if is_applied else "[yellow]⏳[/]"
        
        markers = []
        if item["is_head"]:
            markers.append("[bold cyan]HEAD[/]")
        if item["is_current"]:
            markers.append("[bold green]CURRENT[/]")
            
        marker_str = " | ".join(markers)
        
        table.add_row(
            status_icon,
            item["revision"],
            item["message"],
            marker_str
        )
    
    console.print(table)


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
        asyncio.run(manager.generate(message=message, tenant_isolated=tenant))
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
def db_check(db_url: str | None) -> None:
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

