
import asyncio
import uuid
from typing import List, Optional
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from eden.db import Model, f, Relationship, Reference, Database
from eden.db.base import Base

# Define models exactly as in test_orm_enhanced.py
class EnhancedParent(Model):
    name: str = f()
    children: Mapped[List["EnhancedChild"]] = Relationship(back_populates="parent")

class EnhancedChild(Model):
    name: str = f()
    parent: Mapped["EnhancedParent"] = Reference(back_populates="children")

async def run_repro():
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.connect()
    
    # Manually bind and create tables
    EnhancedParent._bind_db(db)
    EnhancedChild._bind_db(db)
    
    # Create tables
    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("Creating parent...")
    parent = await EnhancedParent.create(name="EnhancedParent 1")
    print(f"Created Parent with ID: {parent.id}")

    print("Creating child...")
    child = await EnhancedChild.create(name="EnhancedChild 1", parent_id=parent.id)
    print(f"Created Child with ID: {child.id} and parent_id: {getattr(child, 'parent_id', 'NONE')}")

    # Check child in DB
    print("\nChecking child table directly...")
    all_children = await EnhancedChild.query().all()
    print(f"All children in DB: {[{'id': c.id, 'parent_id': getattr(c, 'parent_id', 'MISSING')} for c in all_children]}")

    # Reloading parent with prefetch
    print("\nReloading parent with prefetch('children')...")
    fetched_parent = await EnhancedParent.query().prefetch("children").filter(id=parent.id).first()
    
    if fetched_parent:
        print(f"Fetched parent ID: {fetched_parent.id}")
        print(f"Fetched parent children items: {len(fetched_parent.children)}")
        for c in fetched_parent.children:
            print(f"  - Child: {c.name} (parent_id: {c.parent_id})")
        
        if len(fetched_parent.children) == 0:
            print("FAILURE: children list is empty!")
        else:
            print("SUCCESS: children list is populated.")
    else:
        print("FAILURE: parent not found!")

    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(run_repro())
