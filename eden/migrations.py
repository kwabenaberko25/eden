"""
Eden Database Migrations — Alembic Integration

This module provides database migration infrastructure for schema versioning.

Setup:
    1. Run: alembic init migrations
    2. Configure: migrations/env.py for Eden ORM
    3. Create migrations: alembic revision --autogenerate -m "description"
    4. Apply migrations: alembic upgrade head
    5. Rollback: alembic downgrade -1

Usage:
    from eden.migrations import run_migrations, get_migration_history
    
    async def startup():
        await run_migrations()
    
    history = get_migration_history()
    print(f"Current version: {history.current}")
"""

from __future__ import annotations

import logging
import asyncio
from typing import Optional, List, Dict, Any
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timezone
import subprocess
import json

from sqlalchemy import Column, String, DateTime, Text, JSON

logger = logging.getLogger(__name__)


# ============================================================================
# MIGRATION MODELS (must be created in your models.py)
# ============================================================================

"""
Create these tables in your eden/db/models.py:

from eden.db import Model, Column, String, DateTime
from datetime import datetime

class Migration(Model):
    '''Tracks applied database migrations'''
    __tablename__ = 'alembic_version'
    
    version_num: str = Column(String(32), primary_key=True)
    
    class Meta:
        table_name = 'alembic_version'


class MigrationInfo(Model):
    '''Additional migration metadata (optional)'''
    __tablename__ = 'migration_info'
    
    id: int = Column(Integer, primary_key=True)
    version: str = Column(String(32), unique=True, index=True)
    description: str = Column(String(255))
    applied_at: datetime = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    duration_ms: int = Column(Integer)
    status: str = Column(String(20), default='success')  # success, failed
    error_message: str = Column(String(1000), nullable=True)
"""


# ============================================================================
# MIGRATION DATA STRUCTURES
# ============================================================================

@dataclass
class MigrationVersion:
    """Information about a single migration."""
    version_num: str  # e.g., "001_initial_schema"
    description: str
    applied_at: Optional[datetime] = None
    duration_ms: int = 0
    status: str = "pending"  # pending, applied, failed
    
    @property
    def is_applied(self) -> bool:
        return self.status == "applied"


@dataclass
class MigrationHistory:
    """Complete migration history."""
    current_version: Optional[str]
    applied: List[MigrationVersion]
    pending: List[MigrationVersion]
    failed: List[MigrationVersion]
    
    @property
    def current(self) -> Optional[str]:
        """Current schema version."""
        return self.current_version


# ============================================================================
# ALEMBIC ENV TEMPLATE
# ============================================================================

ALEMBIC_ENV_TEMPLATE = '''"""
Alembic environment configuration for Eden ORM.

This is the environment template that should be used in migrations/env.py
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Add your project root to path
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import your database configuration
from eden.config import Config
from eden.db import get_engine, get_models

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for autogenerate support
target_metadata = Base.metadata  # Replace with your sqlalchemy.MetaData


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = Config.DATABASE_URL
    
    context.configure(
        url=configuration["sqlalchemy.url"],
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """Run migrations against a connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = Config.DATABASE_URL
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.begin() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
'''


ALEMBIC_INI_TEMPLATE = '''# Alembic Configuration File
# Path: migrations/alembic.ini

[alembic]
sqlalchemy.url = postgresql://user:password@localhost/eden_db
script_location = migrations
prepend_sys_path = .

[loggers]
keys = root, sqlalchemy.engine

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy.engine]
level = WARN
handlers =
qualname = sqlalchemy.engine

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
'''


# ============================================================================
# MIGRATION MANAGEMENT
# ============================================================================


async def initialize_migrations(
    migrations_dir: str = "migrations",
) -> None:
    """
    Initialize Alembic migrations directory.
    
    Creates the migrations/ folder structure.
    
    Usage:
        await initialize_migrations("./migrations")
    
    Args:
        migrations_dir: Path to migrations directory
        
    Raises:
        RuntimeError: If already initialized
    """
    path = Path(migrations_dir)
    
    if path.exists():
        raise RuntimeError(f"Migrations already initialized at {path}")
    
    # Run: alembic init migrations
    result = subprocess.run(
        ["alembic", "init", migrations_dir],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        raise RuntimeError(f"Failed to initialize migrations: {result.stderr}")
    
    logger.info(f"Migrations initialized at {path}")


async def create_migration(
    message: str,
    autogenerate: bool = True,
) -> str:
    """
    Create a new migration.
    
    Usage:
        version = await create_migration("Add user roles table")
    
    Args:
        message: Migration description
        autogenerate: Auto-detect schema changes
        
    Returns:
        Version number (e.g., "001_add_user_roles_table")
        
    Raises:
        RuntimeError: If migration creation fails
    """
    cmd = ["alembic", "revision"]
    
    if autogenerate:
        cmd.append("--autogenerate")
    
    cmd.extend(["-m", message])
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise RuntimeError(f"Failed to create migration: {result.stderr}")
    
    # Extract version from output
    # Output: Creating /path/to/migrations/versions/001_message.py
    for line in result.stdout.split("\n"):
        if "Creating" in line:
            version = Path(line.split("Creating ")[1].strip()).stem
            logger.info(f"Migration created: {version}")
            return version
    
    raise RuntimeError("Could not determine migration version")


async def apply_migrations(
    target: str = "head",
) -> List[str]:
    """
    Apply pending migrations.
    
    Usage:
        applied = await apply_migrations()  # Apply all pending
        applied = await apply_migrations("002_schema_v2")  # Apply up to version
    
    Args:
        target: Target version ("head", or specific version)
        
    Returns:
        List of applied migration versions
        
    Raises:
        RuntimeError: If upgrade fails
    """
    cmd = ["alembic", "upgrade", target]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise RuntimeError(f"Failed to apply migrations: {result.stderr}")
    
    # Parse applied versions from output
    applied = []
    for line in result.stdout.split("\n"):
        if " -> " in line:
            # Format: "001_initial -> 002_users, done"
            parts = line.split(" -> ")
            if len(parts) >= 2:
                applied.append(parts[1].split(",")[0].strip())
    
    logger.info(f"Applied {len(applied)} migrations")
    return applied


async def rollback_migrations(
    steps: int = 1,
) -> List[str]:
    """
    Rollback migrations.
    
    Usage:
        rolled_back = await rollback_migrations()  # Rollback 1
        rolled_back = await rollback_migrations(3)  # Rollback 3
    
    Args:
        steps: Number of migrations to rollback
        
    Returns:
        List of rolled-back migration versions
        
    Raises:
        RuntimeError: If downgrade fails
    """
    cmd = ["alembic", "downgrade", f"-{steps}"]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise RuntimeError(f"Failed to rollback migrations: {result.stderr}")
    
    logger.warning(f"Rolled back {steps} migrations")
    return []


async def get_migration_status() -> MigrationHistory:
    """
    Get current migration status.
    
    Usage:
        status = await get_migration_status()
        print(f"Current: {status.current_version}")
        print(f"Applied: {len(status.applied)}")
        print(f"Pending: {len(status.pending)}")
    
    Returns:
        MigrationHistory object with current state
    """
    cmd = ["alembic", "current", "-v"]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        logger.warning("Could not get migration status")
        return MigrationHistory(
            current_version=None,
            applied=[],
            pending=[],
            failed=[]
        )
    
    # Parse current version from output
    current_version = None
    for line in result.stdout.split("\n"):
        if "Current" in line:
            # Format: "Current revision for postgresql://... : abc123def456 (head)"
            parts = line.split(":")
            if len(parts) > 1:
                current_version = parts[1].strip().split()[0]
                break
    
    return MigrationHistory(
        current_version=current_version,
        applied=[],
        pending=[],
        failed=[]
    )


async def run_migrations(
    target: str = "head",
    create_missing: bool = False,
) -> None:
    """
    Run migrations (main entry point).
    
    Usage:
        async def startup():
            await run_migrations()
    
    Args:
        target: Target version ("head" by default)
        create_missing: Create migration tables if missing
        
    Raises:
        RuntimeError: If migrations fail
    """
    logger.info("Running database migrations...")
    
    try:
        applied = await apply_migrations(target)
        logger.info(f"✓ Migrations complete ({len(applied)} applied)")
    except RuntimeError as e:
        logger.error(f"✗ Migration failed: {e}")
        if not create_missing:
            raise
        
        logger.info("Attempting to create migration tables...")
        # Retry with table creation
        await apply_migrations(target)


# ============================================================================
# MIGRATION SCRIPT TEMPLATE
# ============================================================================

MIGRATION_SCRIPT_TEMPLATE = '''"""
{description}

Revision ID: {revision_id}
Revises: {down_revision}
Create Date: {create_date}

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '{revision_id}'
down_revision = {down_revision}
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Apply migration changes.
    
    Example upgrades:
        
        # Create table
        op.create_table(
            'users',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('email', sa.String(255), unique=True),
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        )
        
        # Add column
        op.add_column('users', sa.Column('name', sa.String(100)))
        
        # Create index
        op.create_index('ix_users_email', 'users', ['email'])
        
        # Add foreign key
        op.create_foreign_key(
            'fk_posts_user_id',
            'posts',
            'users',
            ['user_id'],
            ['id']
        )
    """
    # Add upgrade steps here
    pass


def downgrade() -> None:
    """
    Rollback migration changes.
    
    Example downgrades:
        
        # Drop table
        op.drop_table('users')
        
        # Drop column
        op.drop_column('users', 'name')
        
        # Drop foreign key
        op.drop_constraint('fk_posts_user_id', 'posts', type_='foreignkey')
    """
    # Add downgrade steps here
    pass
'''


# ============================================================================
# SETUP HELPER
# ============================================================================

def setup_migrations_documentation() -> str:
    """
    Return migration setup documentation.
    
    This can be output to a MIGRATION_GUIDE.md file.
    """
    return """
# Database Migrations Guide

## Setup

1. **Initialize migrations directory:**
   ```
   alembic init migrations
   ```

2. **Configure database URL in migrations/alembic.ini:**
   ```ini
   sqlalchemy.url = postgresql://user:pass@localhost/eden_db
   ```

3. **Update migrations/env.py** with the template from eden/migrations.ALEMBIC_ENV_TEMPLATE

## Creating Migrations

**Auto-generate from model changes:**
```
alembic revision --autogenerate -m "Add user roles table"
```

**Create empty migration:**
```
alembic revision -m "Custom migration"
```

## Running Migrations

**Apply all pending:**
```
alembic upgrade head
```

**Apply one migration:**
```
alembic upgrade +1
```

**Rollback one migration:**
```
alembic downgrade -1
```

**Check current version:**
```
alembic current
```

## Best Practices

1. **Write clear descriptions:**
   - Bad: "version xx"
   - Good: "Add user roles table with permissions"

2. **Test both upgrade and downgrade:**
   ```
   alembic upgrade +1  # Test upgrade
   alembic downgrade -1  # Test rollback
   ```

3. **Keep migrations small:**
   - One logical change per migration
   - Easier to debug and rollback

4. **Review generated migrations:**
   - Auto-generate creates migrations, but review for correctness
   - Ensure proper data migration for schema changes

5. **Use transactions:**
   - All migrations run in transactions
   - Automatic rollback on error
"""


__all__ = [
    # Models
    "MigrationVersion",
    "MigrationHistory",
    # Functions
    "initialize_migrations",
    "create_migration",
    "apply_migrations",
    "rollback_migrations",
    "get_migration_status",
    "run_migrations",
    # Templates
    "ALEMBIC_ENV_TEMPLATE",
    "ALEMBIC_INI_TEMPLATE",
    "MIGRATION_SCRIPT_TEMPLATE",
    # Setup
    "setup_migrations_documentation",
]
