import pytest
from typing import Any
from eden.db import Model, Database
from sqlalchemy import Column, Integer, String
from eden.db.signals import pre_save, post_save

# Mock signal receiver to track calls
pre_save_calls = []
post_save_calls = []

async def on_pre_save(sender, instance, **kwargs):
    pre_save_calls.append(instance)

async def on_post_save(sender, instance, **kwargs):
    post_save_calls.append(instance)

class BulkTestModel(Model):
    __tablename__ = "bulk_test_model"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    
    before_create_called = False
    after_create_called = False
    
    async def before_create(self, session):
        self.before_create_called = True
        
    async def after_create(self, session):
        self.after_create_called = True

@pytest.mark.asyncio
async def test_bulk_create_triggers_lifecycle(db: Database):
    # Setup
    await db.connect(create_tables=True)
    
    # Register signals
    pre_save.connect(on_pre_save, sender=BulkTestModel)
    post_save.connect(on_post_save, sender=BulkTestModel)
    
    try:
        pre_save_calls.clear()
        post_save_calls.clear()
        
        objects = [
            BulkTestModel(name="One"),
            BulkTestModel(name="Two"),
            BulkTestModel(name="Three"),
        ]
        
        # Act
        count = await BulkTestModel.query().bulk_create(objects)
        
        # Assert
        assert count == 3
        assert len(pre_save_calls) == 3
        assert len(post_save_calls) == 3
        
        for obj in objects:
            assert obj.before_create_called is True
            assert obj.after_create_called is True
            assert obj.id is not None
            
    finally:
        # Cleanup signals to avoid side effects on other tests
        pre_save.disconnect(on_pre_save, sender=BulkTestModel)
        post_save.disconnect(on_post_save, sender=BulkTestModel)
