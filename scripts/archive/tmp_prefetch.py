import asyncio
from typing import List
from eden.db import Model, f, Reference, Relationship
from eden.db.session import Database
from sqlalchemy.orm import Mapped
import uuid

class Parent(Model):
    name: Mapped[str] = f()
    children: Mapped[List["Child"]] = Relationship(back_populates="parent")

class Child(Model):
    name: Mapped[str] = f()
    parent_id: Mapped[uuid.UUID] = f(reference=True)
    parent: Mapped["Parent"] = Reference(back_populates="children")

async def main():
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.connect()
    Model._bind_db(db)
    
    # Force mapping
    from sqlalchemy import inspect
    inspect(Parent)
    inspect(Child)
    
    async with db.engine.begin() as conn:
        await conn.run_sync(Model.metadata.create_all)
    
    p = await Parent.create(name="P1")
    c = await Child.create(name="C1", parent_id=p.id)
    
    # Fresh fetch with prefetch
    print("--- Executing query with prefetch ---")
    p_results = await Parent.query().prefetch("children").all()
    print(f"P_results count: {len(p_results)}")
    if p_results:
        p2 = p_results[0]
        print(f"Children in P2: {len(p2.children)}")
        if p2.children:
             print(f"Child 0 ID: {p2.children[0].id}")
    
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
