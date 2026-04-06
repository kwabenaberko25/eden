import asyncio
import uuid
import pytest
from sqlalchemy import text

from eden.db import Database, Model
from eden.db.fields import UUIDField, StringField, ForeignKeyField
from eden.config import get_config
from eden.db.session import SessionResolutionError

class MockCompany(Model):
    __tablename__ = "test_stress_company"
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    name = StringField(max_length=100)

class MockEmployee(Model):
    __tablename__ = "test_stress_employee"
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    name = StringField(max_length=100)
    company_id = ForeignKeyField("test_stress_company.id")
    
    from sqlalchemy.orm import relationship
    company = relationship("MockCompany")

@pytest.fixture(scope="module")
def config():
    c = get_config()
    c.db_strict_session_mode = False
    return c

@pytest.fixture(scope="module")
async def db(config):
    database = Database("sqlite+aiosqlite:///:memory:")
    await database.connect()
    
    # Bind models manually for testing without typical registry load
    MockCompany._bind_db(database)
    MockEmployee._bind_db(database)

    async with database.engine.begin() as conn:
        await conn.run_sync(Model.metadata.create_all)

    yield database
    await database.disconnect()


@pytest.mark.asyncio
async def test_strict_session_mode_blocks_implicit_fallback(db, config):
    # 1. Non-strict initially (should work implicitly via temporary session generator)
    config.db_strict_session_mode = False
    count = await MockCompany.query().count()
    assert count == 0

    # 2. Enable strict mode
    config.db_strict_session_mode = True
    
    try:
        with pytest.raises(SessionResolutionError) as excinfo:
            await MockCompany.query().count()
        assert "STRICT SESSION MODE is enabled" in str(excinfo.value)
    finally:
        # Revert config
        config.db_strict_session_mode = False

@pytest.mark.asyncio
async def test_strict_session_mode_allows_explicit_queries(db, config):
    config.db_strict_session_mode = True

    try:
        async with db.transaction() as session:
            count = await MockCompany.query().count()
            assert count == 0
    finally:
        config.db_strict_session_mode = False

@pytest.mark.asyncio
async def test_concurrent_query_stress_with_large_joins(db, config):
    async with db.transaction() as session:
        c1 = MockCompany(name="Tech Corp")
        session.add(c1)
        await session.flush()
        
        for i in range(10):
            session.add(MockEmployee(name=f"Emp {i}", company_id=c1.id))
        
        c2 = MockCompany(name="Biz LLC")
        session.add(c2)
        await session.flush()
        
        for i in range(5):
            session.add(MockEmployee(name=f"Worker {i}", company_id=c2.id))
            
    # Function simulating a heavy DB operation
    async def worker_job(company_name):
        async with db.transaction() as session:
            res = await MockEmployee.query().filter(company__name=company_name).all()
            return len(res)

    tasks = [
        worker_job("Tech Corp"),
        worker_job("Biz LLC"),
        worker_job("Tech Corp"),
        worker_job("Biz LLC"),
        worker_job("Biz LLC")
    ]
    
    results = await asyncio.gather(*tasks)
    
    assert results[0] == 10
    assert results[1] == 5
    assert results[2] == 10
    assert results[3] == 5
    assert results[4] == 5
