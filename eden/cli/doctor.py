"""
Eden Doctor — Diagnostic utility for identifying environment and project issues.
"""

from __future__ import annotations

import os
import sys
import platform
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from pathlib import Path

def check_env() -> list[tuple[str, str, str]]:
    """Check basic environment info."""
    import eden
    return [
        ("Python Version", sys.version.split()[0], "green"),
        ("Platform", platform.system(), "green"),
        ("Eden Version", getattr(eden, "__version__", "1.0.0"), "green"),
        ("CWD", os.getcwd(), "blue"),
    ]

def check_structure() -> list[tuple[str, str, str]]:
    """Verify project structure."""
    results = []
    
    # Check for eden/ directory or app/
    if Path("eden").exists() or Path("app").exists():
        results.append(("Project Structure", "Valid", "green"))
    else:
        results.append(("Project Structure", "Not found in CWD", "red"))
        
    # Check for .env
    if Path(".env").exists():
        results.append((".env File", "Present", "green"))
    else:
        results.append((".env File", "Missing (run 'eden new' or create manually)", "yellow"))
        
    return results

async def check_db() -> list[tuple[str, str, str]]:
    """Verify database connection and migrations."""
    from eden.config import get_config
    from sqlalchemy.ext.asyncio import create_async_engine
    
    results = []
    db_url = get_config().get_database_url()
    
    if not db_url:
        results.append(("Database URL", "Not configured in environment", "red"))
        return results
        
    results.append(("Database URL", f"{db_url[:15]}...", "blue"))
    
    try:
        from sqlalchemy import text
        engine = create_async_engine(db_url)
        # Try a simple connection
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        results.append(("DB Connection", "Healthy", "green"))
    except Exception as e:
        results.append(("DB Connection", f"Failed: {str(e)[:50]}", "red"))
        
    # Check migrations directory
    if Path("migrations").exists():
        results.append(("Migrations Dir", "Present", "green"))
    else:
        results.append(("Migrations Dir", "Missing (run 'eden db init')", "yellow"))
        
    return results

@click.command()
def doctor() -> None:
    """🕵️ Eden Doctor — Run health checks on your project."""
    console = Console()
    console.print(Panel.fit("Starting Eden Health Check...", style="bold magenta"))
    
    # 1. Environment
    env_table = Table(title="💻 Environment", show_header=False, box=None)
    for name, value, color in check_env():
        env_table.add_row(f"[bold]{name}[/]:", f"[{color}]{value}[/]")
    console.print(env_table)
    
    # 2. Structure
    struct_table = Table(title="📁 Structure", show_header=False, box=None)
    for name, value, color in check_structure():
        struct_table.add_row(f"[bold]{name}[/]:", f"[{color}]{value}[/]")
    console.print(struct_table)
    
    # 3. Database (Async)
    import asyncio
    try:
        db_results = asyncio.run(check_db())
        db_table = Table(title="🗄️ Database", show_header=False, box=None)
        for name, value, color in db_results:
            db_table.add_row(f"[bold]{name}[/]:", f"[{color}]{value}[/]")
        console.print(db_table)
    except Exception as e:
        console.print(f"[red]Could not perform DB checks: {e}[/]")

    console.print("\n[bold green]✨ Doctor visit complete![/]")
