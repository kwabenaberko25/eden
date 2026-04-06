"""
Eden — Tenant Management CLI Commands
"""

from __future__ import annotations

import asyncio
import sys
from typing import TYPE_CHECKING

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from eden.tenancy.models import Tenant
from eden.db import Database
from eden.config import get_config

console = Console()

@click.group(name="tenant")
def tenant() -> None:
    """🏢  Eden Multi-Tenancy — Manage customer organizations and schemas."""
    pass

@tenant.command("list")
def tenant_list() -> None:
    """List all registered tenants and their status."""
    
    async def _list():
        config = get_config()
        from eden.db.session import init_db
        db = init_db(config.get_database_url())
        await db.connect()
        
        async with db.transaction() as session:
            from sqlalchemy import select
            stmt = select(Tenant).order_by(Tenant.name)
            result = await session.execute(stmt)
            tenants = result.scalars().all()
            
            if not tenants:
                console.print(Panel("  [yellow]ℹ️  No tenants found in the database.[/]", border_style="yellow"))
                return
            
            table = Table(title="🏢  Registered Tenants", show_header=True, header_style="bold cyan")
            table.add_column("ID", style="dim", width=8)
            table.add_column("Name", style="bold")
            table.add_column("Slug", style="green")
            table.add_column("Schema", style="magenta")
            table.add_column("Plan", justify="center")
            table.add_column("Status", justify="center")
            
            for t in tenants:
                status = "[green]Active[/]" if t.is_active else "[red]Inactive[/]"
                schema = t.schema_name or "[dim]N/A[/]"
                plan = t.plan or "standard"
                
                table.add_row(
                    str(t.id)[:8],
                    t.name,
                    t.slug,
                    schema,
                    plan.capitalize(),
                    status
                )
            
            console.print(table)
            console.print(f"  [dim]Total: {len(tenants)} tenant(s)[/]\n")

    asyncio.run(_list())

@tenant.command("create")
@click.option("--name", required=True, help="Display name for the organization.")
@click.option("--slug", required=True, help="URL-friendly identifier for the tenant.")
@click.option("--plan", default="standard", help="Subscription plan for the tenant.")
@click.option("--schema", default=None, help="Dedicated PostgreSQL schema name.")
@click.option("--provision", is_flag=True, help="Auto-provision schema tables after creation.")
def tenant_create(name: str, slug: str, plan: str, schema: str | None, provision: bool) -> None:
    """Create a new tenant organization."""
    
    async def _create():
        config = get_config()
        from eden.db.session import init_db
        db = init_db(config.get_database_url())
        await db.connect()
        
        async with db.transaction() as session:
            from sqlalchemy.future import select
            
            # Check for existing slug
            stmt = select(Tenant).where(Tenant.slug == slug)
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if existing:
                console.print(f"  [red]❌ Error: Tenant with slug '{slug}' already exists.[/]", err=True)
                return

            t = Tenant(
                name=name,
                slug=slug,
                plan=plan,
                schema_name=schema,
                is_active=True
            )
            session.add(t)
            console.print(f"  [green]✅ Created tenant '{name}' (slug: {slug}, plan: {plan})[/]")
            
            # Flush to get fields inserted and IDs generated
            await session.flush()
            
            # Trigger creation signal
            from eden.tenancy.signals import tenant_created, tenant_schema_provisioned
            await tenant_created.send(tenant=t)
            
            if provision:
                if not t.schema_name:
                    t.schema_name = f"tenant_{slug.replace('-', '_')}"
                    console.print(f"  [yellow]ℹ️  No schema provided. Using default: '{t.schema_name}'[/]")
                
                console.print(f"  [bold blue]🏗️  Provisioning schema '{t.schema_name}'...[/]")
                try:
                    await t.provision_schema(session)
                    console.print("  [green]✅ Schema provisioned successfully.[/]")
                    await tenant_schema_provisioned.send(tenant=t)
                except Exception as e:
                    console.print(f"  [red]❌ Failed to provision schema: {e}[/]", err=True)
                    # We continue to let the transaction either commit the tenant or rollback 
                    # based on the calling context. For the CLI, if this fails, the whole block
                    # will typically raise, or we can choose to explicitly raise depending on whether
                    # we want to save the tenant anyway. Raising ensures no partial writes.
                    raise
                    
            console.print("\n  [bold green]✨ Tenant setup complete.[/]\n")

    asyncio.run(_create())

@tenant.command("provision")
@click.option("--slug", help="Provision schema for a specific tenant by slug.")
def tenant_provision(slug: str | None) -> None:
    """Provision database schemas for tenants."""
    
    async def _provision():
        config = get_config()
        from eden.db.session import init_db
        db = init_db(config.get_database_url())
        await db.connect()
        
        async with db.transaction() as session:
            from sqlalchemy import select
            if slug:
                stmt = select(Tenant).where(Tenant.slug == slug)
            else:
                stmt = select(Tenant).where(Tenant.schema_name.isnot(None), Tenant.is_active)
                
            result = await session.execute(stmt)
            tenants = result.scalars().all()
            
            if not tenants:
                if slug:
                    console.print(f"  [red]❌ Error: Tenant with slug '{slug}' not found or has no schema_name.[/]", err=True)
                else:
                    console.print("  [yellow]ℹ️  No tenants found requiring provisioning.[/]")
                return
            
            console.print(f"  [bold blue]🏗️  Found {len(tenants)} tenant(s) to provision...[/]\n")
            
            for t in tenants:
                if not t.schema_name:
                    console.print(f"  [yellow]⚠️  Skipping '{t.name}': No schema_name defined.[/]")
                    continue
                    
                console.print(f"  [bold cyan]→ Provisioning '{t.name}'[/] ([magenta]{t.schema_name}[/])...")
                try:
                    await t.provision_schema(session)
                    console.print(f"  [green]✅ Schema '{t.schema_name}' provisioned successfully.[/]")
                except Exception as e:
                    console.print(f"  [red]❌ Failed to provision schema for '{t.name}': {e}[/]", err=True)
            
            console.print("\n  [bold green]✨ Tenant provisioning complete.[/]\n")

    asyncio.run(_provision())

@tenant.command("info")
@click.argument("slug")
def tenant_info(slug: str) -> None:
    """Show detailed information for a specific tenant."""
    
    async def _info():
        config = get_config()
        from eden.db.session import init_db
        db = init_db(config.get_database_url())
        await db.connect()
        
        async with db.transaction() as session:
            from sqlalchemy import select
            stmt = select(Tenant).where(Tenant.slug == slug)
            result = await session.execute(stmt)
            t = result.scalar_one_or_none()
            
            if not t:
                console.print(f"  [red]❌ Error: Tenant with slug '{slug}' not found.[/]", err=True)
                return
            
            status = "[green]Active[/]" if t.is_active else "[red]Inactive[/]"
            
            # Basic info panel
            info_text = (
                f"[bold]Name:[/] {t.name}\n"
                f"[bold]Slug:[/] {t.slug}\n"
                f"[bold]ID:[/] {t.id}\n"
                f"[bold]Status:[/] {status}\n"
                f"[bold]Plan:[/] {t.plan or 'standard'}\n"
                f"[bold]Schema:[/] [magenta]{t.schema_name or 'N/A'}[/]"
            )
            
            console.print(Panel(info_text, title=f"🏢 Tenant: {t.name}", border_style="cyan", expand=False))

    asyncio.run(_info())
