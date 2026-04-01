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
        db = Database(config.get_database_url())
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

@tenant.command("provision")
@click.option("--slug", help="Provision schema for a specific tenant by slug.")
def tenant_provision(slug: str | None) -> None:
    """Provision database schemas for tenants."""
    
    async def _provision():
        config = get_config()
        db = Database(config.get_database_url())
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
        db = Database(config.get_database_url())
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
