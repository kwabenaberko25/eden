import pytest
import uuid
import datetime
from sqlalchemy import select
from eden.db import Model, StringField, SoftDeleteMixin, Database
from eden.db.mixins.lifecycle import LifecycleMixin

class SoftDeleteModel(Model, SoftDeleteMixin):
    __tablename__ = "soft_delete_models"
    name: str = StringField()

class SaveModel(Model, LifecycleMixin):
    __tablename__ = "save_models"
    name: str = StringField()

@pytest.mark.asyncio
async def test_soft_delete_commit_false_rollback(db: Database):
    """
    Verifies that SoftDeleteMixin.delete(commit=False) is rolled back
    if the transaction is not committed.
    """
    # 1. Setup
    instance = SoftDeleteModel(name="RollbackMe")
    await instance.save()
    instance_id = instance.id
    
    # 2. Try to soft delete but fail the transaction
    try:
        async with db.transaction() as session:
            # We must use instance with the session
            await instance.delete(session=session, commit=False)
            assert instance.deleted_at is not None
            raise ValueError("Forced Rollback")
    except ValueError:
        pass
        
    # 3. Verify it's NOT soft-deleted in the database
    async with db.session() as session:
        # Use instance_id directly to avoid expired object issues
        stmt = select(SoftDeleteModel).where(SoftDeleteModel.id == instance_id)
        result = await session.execute(stmt)
        found = result.scalar_one_or_none()
        assert found is not None
        assert found.deleted_at is None

@pytest.mark.asyncio
async def test_save_commit_false_rollback(db: Database):
    """
    Verifies that save(commit=False) is rolled back if transaction fails.
    """
    # 1. Try to save but fail the transaction
    instance_id = None
    try:
        async with db.transaction() as session:
            instance = SaveModel(name="RollbackSave")
            await instance.save(session=session, commit=False)
            instance_id = instance.id
            assert instance_id is not None
            raise ValueError("Forced Rollback")
    except ValueError:
        pass
        
    # 2. Verify it is NOT in the database
    async with db.session() as session:
        stmt = select(SaveModel).where(SaveModel.id == instance_id)
        result = await session.execute(stmt)
        assert result.scalar_one_or_none() is None
