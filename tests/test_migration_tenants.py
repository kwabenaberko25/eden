"""
Tests for MigrationManager.migrate_tenants improvements (Issue #12).

Verifies:
1. Returns result dict with per-tenant status
2. continue_on_error=True continues past failures
3. continue_on_error=False raises on first failure
4. Empty tenant list returns empty dict
"""

import pytest
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from eden.db.migrations import MigrationManager, MigrationError


class FakeTenantRow:
    """Simulate a SQLAlchemy Row from tenant query."""
    def __init__(self, schema_name, name):
        self.schema_name = schema_name
        self.name = name


def make_mock_engine(tenants):
    """Create a properly mocked async engine that returns tenant rows."""
    mock_result = MagicMock()
    mock_result.all.return_value = tenants
    
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value=mock_result)
    
    @asynccontextmanager
    async def fake_connect():
        yield mock_conn
    
    mock_engine = MagicMock()
    mock_engine.connect = fake_connect
    mock_engine.dispose = AsyncMock()
    
    return mock_engine


class TestMigrateTenants:
    """Test improved migrate_tenants method."""
    
    @pytest.mark.asyncio
    async def test_returns_result_dict(self):
        """migrate_tenants should return a dict of {schema: status}."""
        mgr = MigrationManager.__new__(MigrationManager)
        mgr.config = MagicMock()
        mgr.config.get_main_option.return_value = "sqlite+aiosqlite:///:memory:"
        
        tenants = [
            FakeTenantRow("tenant_a", "Tenant A"),
            FakeTenantRow("tenant_b", "Tenant B"),
        ]
        
        mock_engine = make_mock_engine(tenants)
        
        with patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine):
            with patch.object(mgr, "migrate", new_callable=AsyncMock) as mock_migrate:
                results = await mgr.migrate_tenants()
        
        assert results["tenant_a"] == "ok"
        assert results["tenant_b"] == "ok"
        assert mock_migrate.call_count == 2
    
    @pytest.mark.asyncio
    async def test_continue_on_error_true(self):
        """Should continue to next tenant after a failure."""
        mgr = MigrationManager.__new__(MigrationManager)
        mgr.config = MagicMock()
        mgr.config.get_main_option.return_value = "sqlite+aiosqlite:///:memory:"
        
        tenants = [
            FakeTenantRow("tenant_a", "Tenant A"),
            FakeTenantRow("tenant_b", "Tenant B"),
            FakeTenantRow("tenant_c", "Tenant C"),
        ]
        
        mock_engine = make_mock_engine(tenants)
        
        async def fake_migrate(revision="head", schema=None):
            if schema == "tenant_b":
                raise Exception("Connection lost")
        
        with patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine):
            with patch.object(mgr, "migrate", side_effect=fake_migrate):
                results = await mgr.migrate_tenants(continue_on_error=True)
        
        assert results["tenant_a"] == "ok"
        assert "error" in results["tenant_b"]
        assert results["tenant_c"] == "ok"
    
    @pytest.mark.asyncio
    async def test_continue_on_error_false(self):
        """Should raise MigrationError on first failure."""
        mgr = MigrationManager.__new__(MigrationManager)
        mgr.config = MagicMock()
        mgr.config.get_main_option.return_value = "sqlite+aiosqlite:///:memory:"
        
        tenants = [
            FakeTenantRow("tenant_a", "Tenant A"),
            FakeTenantRow("tenant_b", "Tenant B"),
        ]
        
        mock_engine = make_mock_engine(tenants)
        
        async def fake_migrate(revision="head", schema=None):
            raise Exception("DB down")
        
        with patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine):
            with patch.object(mgr, "migrate", side_effect=fake_migrate):
                with pytest.raises(MigrationError, match="aborted"):
                    await mgr.migrate_tenants(continue_on_error=False)
    
    @pytest.mark.asyncio
    async def test_empty_tenants(self):
        """Empty tenant list should return empty dict."""
        mgr = MigrationManager.__new__(MigrationManager)
        mgr.config = MagicMock()
        mgr.config.get_main_option.return_value = "sqlite+aiosqlite:///:memory:"
        
        mock_engine = make_mock_engine([])
        
        with patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine):
            results = await mgr.migrate_tenants()
        
        assert results == {}
