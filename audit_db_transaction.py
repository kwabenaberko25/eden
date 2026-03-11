import pytest
import uuid
import os
import asyncio
from datetime import datetime
from pydantic import ValidationError

from eden.db import Model, Database
from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy import String, Integer, inspect

class UserTransaction(Model):
    __tablename__ = "test_transaction_users"
    name: Mapped[str] = mapped_column(String)
    age: Mapped[int] = mapped_column(Integer, default=0)

    # We will trigger an exception in the after_save hook
    async def after_save(self, session):
        if self.name == "trigger_rollback":
            raise ValueError("Something went wrong in after_save!")

@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="module")
async def db_instance():
    # Setup test DB
    test_db_url = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
    db = Database(test_db_url)
    Model._bind_db(db)
    
    async with db.engine.begin() as conn:
        await conn.run_sync(Model.registry.metadata.drop_all)
        await conn.run_sync(Model.registry.metadata.create_all)
        
    yield db
    
    async with db.engine.begin() as conn:
        await conn.run_sync(Model.registry.metadata.drop_all)
    await db.disconnect()

@pytest.mark.asyncio
async def test_transaction_integrity_after_save_failure(db_instance):
    # Test valid save
    user = await UserTransaction.create(name="valid_user")
    assert getattr(user, "id", None) is not None
    
    # Verify it exists
    db_user = await UserTransaction.get(id=user.id)
    assert db_user.name == "valid_user"
    
    # Test save that triggers exception in post hook
    try:
        await UserTransaction.create(name="trigger_rollback")
        pytest.fail("Should have raised ValueError")
    except ValueError as e:
        assert str(e) == "Something went wrong in after_save!"
        
    # The transaction should have been rolled back, meaning it shouldn't exist in the DB!
    results = await UserTransaction.filter(name="trigger_rollback").all()
    assert len(results) == 0, "Transaction integrity compromised! Data persisted despite after_save exception."

    # Test bulk_create save that triggers exception
    try:
        await UserTransaction.bulk_create([
            UserTransaction(name="valid_bulk_user"),
            UserTransaction(name="trigger_rollback")
        ])
        pytest.fail("Should have raised ValueError")
    except ValueError as e:
        pass
        
    # Valid bulk user shouldn't exist because the entire batch should be rolled back
    results_bulk = await UserTransaction.filter(name="valid_bulk_user").all()
    assert len(results_bulk) == 0, "Transaction integrity compromised! Partial bulk_create persisted."
