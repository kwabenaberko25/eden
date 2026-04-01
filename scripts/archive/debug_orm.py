
import asyncio
from eden.db import Database, Model, f, Reference, Relationship, QuerySet
from sqlalchemy.orm import Mapped
from typing import List

class EnhancedParent(Model):
    name: str = f()
    children: Mapped[List["EnhancedChild"]] = Relationship(back_populates="parent")

class EnhancedChild(Model):
    name: str = f()
    parent: Mapped["EnhancedParent"] = Reference(back_populates="children")

async def run_test():
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.connect(create_tables=True)
    
    print(f"DEBUG: EnhancedParent table: {EnhancedParent.__tablename__}")
    print(f"DEBUG: EnhancedChild table: {EnhancedChild.__tablename__}")
    
    parent = await EnhancedParent.create(name="Parent 1")
    child = await EnhancedChild.create(name="Child 1", parent_id=parent.id)
    
    print(f"DEBUG: Child ID: {child.id}")
    print(f"DEBUG: Child parent_id: {child.parent_id}")
    
    fetched_parent = await EnhancedParent.query().prefetch("children").filter(id=parent.id).first()
    print(f"DEBUG: Fetched parent ID: {fetched_parent.id}")
    print(f"DEBUG: Children count: {len(fetched_parent.children)}")
    
    # Try select_related
    fetched_child = await EnhancedChild.query().select_related("parent").filter(id=child.id).first()
    print(f"DEBUG: Fetched child parent name: {fetched_child.parent.name}")
    
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(run_test())
