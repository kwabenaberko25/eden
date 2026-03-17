import pytest
import asyncio
from eden.db import Database, atomic
from sqlalchemy import text

@pytest.mark.asyncio
async def test_engine_reuse_for_isolation_levels():
    """Verify that multiple transactions with same isolation level reuse the same branched engine."""
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.connect(create_tables=True)
    
    # First call - creates branched engine
    async with db.transaction(isolation_level="SERIALIZABLE") as s1:
        engine1 = s1.bind
        await s1.execute(text("SELECT 1"))
        
    # Second call - should reuse same branched engine instance
    async with db.transaction(isolation_level="SERIALIZABLE") as s2:
        engine2 = s2.bind
        await s2.execute(text("SELECT 1"))
        
    assert engine1 is engine2, "Engines for same isolation level were not reused"
    
    # Different isolation level should have different engine
    async with db.transaction(isolation_level="READ UNCOMMITTED") as s3:
        engine3 = s3.bind
        await s3.execute(text("SELECT 1"))
        
    assert engine3 is not engine1, "Different isolation levels shared the same engine"
    
    await db.disconnect()

@pytest.mark.asyncio
async def test_isolation_level_actually_applied():
    """Verify that the isolation level is correctly propagated to the connection."""
    # SQLite support for isolation levels in aiosqlite is specific.
    # We verify that the engine options contain the requested level.
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.connect()
    
    level = "SERIALIZABLE"
    async with db.transaction(isolation_level=level) as session:
        # Check execution options of the bind (engine)
        assert session.bind.get_execution_options().get("isolation_level") == level
        
    await db.disconnect()
