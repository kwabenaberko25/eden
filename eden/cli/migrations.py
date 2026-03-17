"""
Eden CLI - Database Migrations

Provides commands for managing database schema changes using Alembic.

Usage:
    eden makemigrations --message "Add new table"
    eden migrate
    eden migrate --down
"""

import asyncio
import os
from typing import Optional, Any
from pathlib import Path
import subprocess
import sys
import click


from eden.db.migrations import MigrationManager as DbMigrationManager
from eden.db.session import get_db

class MigrationException(Exception):
    """Base exception for migration errors."""
    pass

class MigrationNotFound(MigrationException):
    """Raised when a revision is not found."""
    pass

class MigrationManager:
    """
    CLI Proxy for Database Migration Management.
    """
    
    def __init__(self, db_url: Optional[str] = None, migrations_dir: str = "migrations"):
        self.db_url = db_url or os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///db.sqlite")
        self.migrations_dir = migrations_dir
    
    async def _run_alembic(self, command_name: str, *args, **kwargs) -> Any:
        # Integrated implementation using DbMigrationManager
        manager = DbMigrationManager(self.db_url)
        
        if command_name == "init":
            return await asyncio.to_thread(manager.init)
        elif command_name == "revision":
            return await asyncio.to_thread(manager.generate, kwargs.get("message", "Auto migration"))
        elif command_name == "upgrade":
            revision = args[0] if args else "head"
            return await asyncio.to_thread(manager.migrate, revision)
        elif command_name == "downgrade":
            revision = args[0] if args else "-1"
            return await asyncio.to_thread(manager.downgrade, revision)
        elif command_name == "current":
            if hasattr(manager, "current"):
                return await asyncio.to_thread(manager.current)
            # Fallback to subprocess for current as it might not be in DbMigrationManager yet
            import subprocess
            cmd = ["alembic", "current"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.stdout.strip()
        elif command_name == "history":
            return await asyncio.to_thread(manager.history)
        elif command_name == "stamp":
            if hasattr(manager, "stamp"):
                return await asyncio.to_thread(manager.stamp, args[0] if args else "head")
            # Fallback
            import subprocess
            cmd = ["alembic", "stamp", args[0] if args else "head"]
            subprocess.run(cmd, capture_output=True, text=True)
            return None
        
        raise MigrationException(f"Unsupported migration command: {command_name}")

    async def init_migrations(self) -> None:
        await self._run_alembic("init")
        click.echo(f"✓ Initialized migrations at '{self.migrations_dir}'")
    
    async def make_migrations(
        self,
        message: Optional[str] = None,
        autogenerate: bool = True,
    ) -> str:
        revision = await self._run_alembic("revision", message=message, autogenerate=autogenerate)
        click.echo("✓ Migration created successfully")
        return revision
    
    async def migrate(self, revision: str = "head") -> None:
        try:
            await self._run_alembic("upgrade", revision)
        except Exception as e:
            if "not found" in str(e).lower():
                raise MigrationNotFound(str(e))
            raise MigrationException(str(e))
        click.echo(f"✓ Database migrated to {revision} successfully")
    
    async def downgrade(self, revision: str = "-1") -> None:
        try:
            await self._run_alembic("downgrade", revision)
        except Exception as e:
            raise MigrationException(str(e))
        click.echo(f"✓ Migration rollback to {revision} successful")
    
    async def current(self) -> str:
        return await self._run_alembic("current")
    
    async def history(self) -> list[str]:
        return await self._run_alembic("history") or []

    async def stamp(self, revision: str = "head") -> None:
        """Mark a revision without running it."""
        await self._run_alembic("stamp", revision)
        click.echo(f"✓ Stamped to {revision}")


# CLI Interface
async def cli_makemigrations(message: Optional[str] = None, manager: Optional[MigrationManager] = None) -> None:
    """CLI: Create a new migration."""
    manager = manager or MigrationManager()
    await manager.make_migrations(message=message)


async def cli_migrate(manager: Optional[MigrationManager] = None) -> None:
    """CLI: Apply migrations."""
    manager = manager or MigrationManager()
    await manager.migrate()


async def cli_downgrade(manager: Optional[MigrationManager] = None) -> None:
    """CLI: Rollback migrations."""
    manager = manager or MigrationManager()
    await manager.downgrade()


async def cli_migration_history(manager: Optional[MigrationManager] = None) -> None:
    """CLI: Show migration history."""
    manager = manager or MigrationManager()
    await manager.history()
