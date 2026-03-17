import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from eden.db import MigrationManager

@pytest.mark.asyncio
async def test_migration_check_drift_detection():
    """Verify that MigrationManager.check detects mismatches between head and tenants."""
    db_url = "sqlite+aiosqlite:///:memory:"
    
    # 1. Mock the shared schema version and tenants
    mock_shared_res = MagicMock()
    mock_shared_res.scalar.return_value = "v2" # Shared is OK
    
    mock_tenants_res = MagicMock()
    mock_t1 = MagicMock(schema_name="tenant1")
    mock_t2 = MagicMock(schema_name="tenant2")
    mock_tenants_res.scalars.return_value.all.return_value = [mock_t1, mock_t2]
    
    mock_t1_res = MagicMock()
    mock_t1_res.scalar.return_value = "v2" # Tenant 1 is OK
    
    mock_t2_res = MagicMock()
    mock_t2_res.scalar.return_value = "v1" # Tenant 2 is DRIFTED
    
    # 2. Mock create_async_engine
    with patch("sqlalchemy.ext.asyncio.create_async_engine") as mock_create_engine:
        mock_engine = mock_create_engine.return_value
        mock_conn = AsyncMock()
        mock_engine.connect.return_value.__aenter__.return_value = mock_conn
        mock_engine.dispose = AsyncMock()
        
        # Setup session.execute side effects
        mock_conn.execute.side_effect = [
            mock_shared_res,  # Shared version check
            mock_tenants_res, # Tenant list fetch
            mock_t1_res,      # Tenant 1 version check
            mock_t2_res,      # Tenant 2 version check
        ]
        
        # 3. Mock Alembic ScriptDirectory
        with patch("alembic.script.ScriptDirectory.from_config") as mock_from_config:
            mock_sd = mock_from_config.return_value
            mock_sd.get_current_head.return_value = "v2"
            
            manager = MigrationManager(db_url)
            # Bypass config loading
            manager.config = MagicMock()
            manager.config.get_main_option.return_value = db_url
            
            # 4. Run check
            results = await manager.check()
            
            # 5. Verify assertions
            assert results["shared"] == "ok"
            assert results["tenant1"] == "ok"
            assert "drifted" in results["tenant2"]
            assert "expected v2, got v1" in results["tenant2"]
