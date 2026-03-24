
import pytest
import asyncio
from eden.db import Model, StringField
from sqlalchemy import select

class TestModel(Model):
    name: str = StringField(max_length=100)

@pytest.mark.asyncio
async def test_save_commit_false_reproduction(db):
    """
    Verifies that save(commit=False) actually defers the commit.
    """
    # 1. Start a transaction with commit=False
    async with db.transaction(commit=False) as session:
        # Create with commit=False (deferred within this transaction)
        instance = await TestModel.create(session=session, name="Partial", commit=False)
        instance_id = instance.id
        assert instance_id is not None
        
        # Note: In SQLite StaticPool, it might be visible via flush() on same connection,
        # but once we exit this block without commit, it must be GONE.
    
    # 2. Check if it's in the DB using a NEW transaction
    async with db.transaction() as new_session:
        # get() will return None if it wasn't committed
        found = await TestModel.get(id=instance_id, session=new_session)
        assert found is None, "Record was persisted even though commit=False was passed"
        
    # 3. Verify that if we DO commit, it works
    async with db.transaction(commit=True) as session:
        instance = await TestModel.create(session=session, name="Persistent", commit=True)
        instance_id = instance.id
        
    async with db.transaction() as next_session:
        found = await TestModel.get(id=instance_id, session=next_session)
        assert found is not None
        assert found.name == "Persistent"
