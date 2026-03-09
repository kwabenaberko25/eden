import pytest
import uuid
from datetime import datetime
from eden.db import Model, f, Mapped, Uuid

class Task(Model):
    title: str = f(max_length=100)
    is_done: bool = f(default=False)

@pytest.mark.asyncio
async def test_orm_basic_crud(db):
    # 1. Create
    task = await Task.create(title="Finish Audit", is_done=False)
    assert task.id is not None
    assert isinstance(task.id, uuid.UUID)
    assert task.title == "Finish Audit"
    assert task.is_done is False
    assert isinstance(task.created_at, datetime)
    assert isinstance(task.updated_at, datetime)

    # 2. Read (get)
    fetched = await Task.get(task.id)
    assert fetched is not None
    assert fetched.id == task.id
    assert fetched.title == "Finish Audit"

    # 3. Update
    await fetched.update(is_done=True, title="Audit Finished")
    assert fetched.is_done is True
    assert fetched.title == "Audit Finished"
    
    # Verify in DB
    refetched = await Task.get(task.id)
    assert refetched.is_done is True
    assert refetched.title == "Audit Finished"

    # 4. Delete
    await refetched.delete()
    deleted = await Task.get(task.id)
    assert deleted is None

@pytest.mark.asyncio
async def test_orm_id_generation(db):
    # Test that UUIDs are unique and auto-generated
    t1 = await Task.create(title="Task 1")
    t2 = await Task.create(title="Task 2")
    assert t1.id != t2.id
    assert isinstance(t1.id, uuid.UUID)

@pytest.mark.asyncio
async def test_orm_timestamps(db):
    task = await Task.create(title="Timestamp Test")
    created_at = task.created_at
    updated_at = task.updated_at
    
    import asyncio
    await asyncio.sleep(1.1)
    
    await task.update(title="Updated")
    assert task.updated_at > updated_at
    assert task.created_at == created_at

@pytest.mark.asyncio
async def test_orm_all_and_count(db):
    # Clear and add items
    await Task.create(title="A")
    await Task.create(title="B")
    
    tasks = await Task.all()
    assert len(tasks) >= 2
    
    count = await Task.count()
    assert count >= 2
