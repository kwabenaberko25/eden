"""
Eden ORM - Migrations

Track and apply schema migrations to PostgreSQL.
"""

import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

from ..connection import get_session

logger = logging.getLogger(__name__)


class MigrationRunner:
    """Executes migration files in sequence."""
    
    def __init__(self, migrations_dir: str = "migrations"):
        self.migrations_dir = Path(migrations_dir)
        self.migrations_dir.mkdir(exist_ok=True)
        self.applied_migrations: List[str] = []
    
    async def initialize(self):
        """Create migration tracking table."""
        session = await get_session()
        
        # Create schema_versions table if it doesn't exist
        sql = """
        CREATE TABLE IF NOT EXISTS schema_versions (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) UNIQUE NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        try:
            await session.execute(sql)
            logger.info("Migration tracking table initialized")
        except Exception as e:
            logger.error(f"Failed to initialize migration table: {e}")
    
    async def get_applied_migrations(self) -> List[str]:
        """Get list of already-applied migrations."""
        session = await get_session()
        
        try:
            rows = await session.fetch(
                "SELECT name FROM schema_versions ORDER BY applied_at"
            )
            return [row['name'] for row in rows]
        except Exception:
            return []
    
    async def get_pending_migrations(self) -> List[str]:
        """Get list of migrations not yet applied."""
        applied = await self.get_applied_migrations()
        
        migration_files = sorted([
            f.stem for f in self.migrations_dir.glob("*.sql")
            if f.stem.startswith("m_")
        ])
        
        return [m for m in migration_files if m not in applied]
    
    async def apply(self, name: str):
        """Apply a single migration."""
        migration_file = self.migrations_dir / f"{name}.sql"
        
        if not migration_file.exists():
            logger.warning(f"Migration file not found: {migration_file}")
            return False
        
        session = await get_session()
        
        try:
            with open(migration_file, 'r') as f:
                sql = f.read()
            
            await session.execute(sql)
            
            # Record migration
            await session.execute(
                "INSERT INTO schema_versions (name) VALUES ($1)",
                name
            )
            
            logger.info(f"Applied migration: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Migration {name} failed: {e}")
            return False
    
    async def apply_pending(self):
        """Apply all pending migrations."""
        await self.initialize()
        
        pending = await self.get_pending_migrations()
        
        if not pending:
            logger.info("No pending migrations")
            return True
        
        logger.info(f"Applying {len(pending)} migrations")
        
        for migration in pending:
            success = await self.apply(migration)
            if not success:
                logger.error(f"Stopped at migration: {migration}")
                return False
        
        logger.info("All migrations applied successfully")
        return True


async def apply_migrations(migrations_dir: str = "migrations") -> bool:
    """Apply all pending migrations."""
    runner = MigrationRunner(migrations_dir)
    return await runner.apply_pending()


async def create_migration(name: str, sql: str, migrations_dir: str = "migrations"):
    """Create a new migration file."""
    runner = MigrationRunner(migrations_dir)
    
    # Generate migration name with timestamp
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    migration_name = f"m_{timestamp}_{name}"
    migration_file = runner.migrations_dir / f"{migration_name}.sql"
    
    with open(migration_file, 'w') as f:
        f.write(f"-- Migration: {migration_name}\n")
        f.write(f"-- Created: {datetime.now().isoformat()}\n\n")
        f.write(sql)
    
    logger.info(f"Created migration: {migration_name}")
    return migration_name
