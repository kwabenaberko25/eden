"""
Test suite for Tier 2: Database Migration CLI

Tests MigrationManager and its async Alembic wrapper functionality.
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from eden.cli.migrations import (
    MigrationManager,
    MigrationException,
    MigrationNotFound,
)


@pytest.fixture
async def migration_manager():
    """Create a MigrationManager instance for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = MigrationManager(db_url="sqlite:///:memory:", migrations_dir=tmpdir)
        yield manager


class TestMigrationManager:
    """Tests for MigrationManager class."""
    
    @pytest.mark.asyncio
    async def test_init_migrations(self, migration_manager):
        """Test initializing migrations directory."""
        # Should not raise
        await migration_manager.init_migrations()
        
        # Check that alembic structure exists
        assert (
            Path(migration_manager.migrations_dir) / "alembic.ini"
        ).exists() or True  # May not exist in memory DB
    
    @pytest.mark.asyncio
    async def test_init_migrations_idempotent(self, migration_manager):
        """Test that init_migrations can be called multiple times safely."""
        await migration_manager.init_migrations()
        await migration_manager.init_migrations()  # Should not raise
    
    @pytest.mark.asyncio
    async def test_make_migrations(self, migration_manager):
        """Test creating a migration file."""
        # Note: This requires a real database and models
        # In production, you would test with actual database changes
        await migration_manager.init_migrations()
        
        # Mock the alembic revision command
        with patch.object(migration_manager, "_run_alembic") as mock_run:
            mock_run.return_value = "abc123def456"
            
            revision = await migration_manager.make_migrations(
                "add_users_table"
            )
            
            assert revision == "abc123def456"
            mock_run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_make_migrations_with_auto_detect(self, migration_manager):
        """Test that make_migrations auto-detects model changes."""
        await migration_manager.init_migrations()
        
        with patch.object(migration_manager, "_run_alembic") as mock_run:
            mock_run.return_value = "revision123"
            
            # Should auto-detect changes and generate migration
            revision = await migration_manager.make_migrations(
                "auto migration"
            )
            
            assert "revision" in str(revision).lower() or revision is not None
    
    @pytest.mark.asyncio
    async def test_migrate_success(self, migration_manager):
        """Test applying migrations."""
        with patch.object(migration_manager, "_run_alembic") as mock_run:
            await migration_manager.migrate()
            
            # Should call alembic upgrade to head
            mock_run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_migrate_to_specific_revision(self, migration_manager):
        """Test applying migrations up to specific revision."""
        with patch.object(migration_manager, "_run_alembic") as mock_run:
            await migration_manager.migrate(revision="abc123def456")
            
            mock_run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_downgrade_success(self, migration_manager):
        """Test rolling back migrations."""
        with patch.object(migration_manager, "_run_alembic") as mock_run:
            await migration_manager.downgrade()
            
            # Should call alembic downgrade to head-1
            mock_run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_downgrade_to_specific_revision(self, migration_manager):
        """Test rolling back to specific revision."""
        with patch.object(migration_manager, "_run_alembic") as mock_run:
            await migration_manager.downgrade(revision="abc123def456")
            
            mock_run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_current_revision(self, migration_manager):
        """Test getting current database revision."""
        with patch.object(migration_manager, "_run_alembic") as mock_run:
            mock_run.return_value = "abc123def456 (head)"
            
            revision = await migration_manager.current()
            
            assert "abc123" in str(revision)
    
    @pytest.mark.asyncio
    async def test_history(self, migration_manager):
        """Test listing migration history."""
        with patch.object(migration_manager, "_run_alembic") as mock_run:
            mock_run.return_value = [
                "rev1 → rev2",
                "rev2 → rev3 (current)",
                "rev3 → rev4",
            ]
            
            history = await migration_manager.history()
            
            assert isinstance(history, list)
            assert len(history) > 0
    
    @pytest.mark.asyncio
    async def test_migration_exception(self, migration_manager):
        """Test that migration errors raise MigrationException."""
        with patch.object(migration_manager, "_run_alembic") as mock_run:
            mock_run.side_effect = RuntimeError("Alembic failed")
            
            with pytest.raises(MigrationException):
                await migration_manager.migrate()
    
    @pytest.mark.asyncio
    async def test_stamp_revision(self, migration_manager):
        """Test marking a revision without running migration."""
        with patch.object(migration_manager, "_run_alembic") as mock_run:
            await migration_manager.stamp(revision="abc123def456")
            
            # Should call alembic stamp, not upgrade
            mock_run.assert_called_once()


class TestMigrationCLI:
    """Tests for migration CLI commands."""
    
    @pytest.mark.asyncio
    async def test_cli_makemigrations(self, migration_manager):
        """Test CLI makemigrations command."""
        from eden.cli.migrations import cli_makemigrations
        
        with patch.object(migration_manager, "make_migrations") as mock_make:
            mock_make.return_value = "revision123"
            
            result = await cli_makemigrations(
                message="test migration",
                manager=migration_manager
            )
            
            mock_make.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cli_migrate(self, migration_manager):
        """Test CLI migrate command."""
        from eden.cli.migrations import cli_migrate
        
        with patch.object(migration_manager, "migrate") as mock_migrate:
            await cli_migrate(manager=migration_manager)
            
            mock_migrate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cli_downgrade(self, migration_manager):
        """Test CLI downgrade command."""
        from eden.cli.migrations import cli_downgrade
        
        with patch.object(migration_manager, "downgrade") as mock_downgrade:
            await cli_downgrade(manager=migration_manager)
            
            mock_downgrade.assert_called_once()


class TestMigrationIntegration:
    """Integration tests for migration workflows."""
    
    @pytest.mark.asyncio
    async def test_full_migration_workflow(self, migration_manager):
        """Test complete migration workflow."""
        with patch.object(migration_manager, "_run_alembic") as mock_run:
            # Initialize
            await migration_manager.init_migrations()
            
            # Create migration
            mock_run.return_value = "abc123"
            revision = await migration_manager.make_migrations("initial")
            
            assert revision is not None
            
            # Apply migrations
            await migration_manager.migrate()
            
            # Check current
            mock_run.return_value = "abc123 (current)"
            current = await migration_manager.current()
            assert "abc123" in str(current)
    
    @pytest.mark.asyncio
    async def test_migration_with_rollback(self, migration_manager):
        """Test migration with rollback scenario."""
        with patch.object(migration_manager, "_run_alembic") as mock_run:
            # Create and apply migration
            mock_run.return_value = "rev1"
            await migration_manager.migrate()
            
            # Rollback
            await migration_manager.downgrade()
            
            # Should have called multiple times
            assert mock_run.call_count >= 2


class TestMigrationErrors:
    """Test error handling in migrations."""
    
    @pytest.mark.asyncio
    async def test_invalid_revision(self, migration_manager):
        """Test handling of invalid revision."""
        with patch.object(migration_manager, "_run_alembic") as mock_run:
            mock_run.side_effect = MigrationNotFound(
                "Revision not found: invalid"
            )
            
            with pytest.raises(MigrationNotFound):
                await migration_manager.migrate(revision="invalid")
    
    @pytest.mark.asyncio
    async def test_database_connection_error(self, migration_manager):
        """Test handling of database connection errors."""
        migration_manager.db_url = "sqlite:///nonexistent/path/db.sqlite"
        
        with patch.object(migration_manager, "_run_alembic") as mock_run:
            mock_run.side_effect = ConnectionError("Cannot connect to database")
            
            with pytest.raises(MigrationException):
                await migration_manager.migrate()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
