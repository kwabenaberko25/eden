import pytest
import asyncio
import uuid
from typing import List
from sqlalchemy.orm import Mapped
from eden.db import Model, f, Database

# ── Audit Models ──────────────────────────────────────────────────────────

class GrandParent(Model):
    __tablename__ = "grandparents"
    name: Mapped[str] = f()
    # Explicitly use Relationship to avoid SA 2.0 ArgumentError in tests
    children: Mapped[List["Parent"]] = f(back_populates="grandparent")

class Parent(Model):
    __tablename__ = "parents"
    name: Mapped[str] = f()
    grandparent_id: Mapped[uuid.UUID] = f(foreign_key="grandparents.id")
    grandparent: Mapped["GrandParent"] = f(back_populates="children")
    children: Mapped[List["Child"]] = f(back_populates="parent")

class Child(Model):
    __tablename__ = "children"
    name: Mapped[str] = f()
    parent_id: Mapped[uuid.UUID] = f(foreign_key="parents.id")
    parent: Mapped["Parent"] = f(back_populates="children")

# ── Audit Tests ───────────────────────────────────────────────────────────

@pytest.fixture
async def join_db():
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.connect()
    
    async with db.engine.begin() as conn:
        await conn.run_sync(Model.metadata.create_all)
        
    async with db.session() as session:
        gp = await GrandParent.create(session, name="GP1")
        p = await Parent.create(session, name="P1", grandparent_id=gp.id)
        c = await Child.create(session, name="C1", parent_id=p.id)
        await session.commit()
        
    yield db
    await db.disconnect()

@pytest.mark.asyncio
async def test_auto_join_involvement(join_db):
    """
    AUDIT 2.2: Auto-Join Stress.
    Verify that deep relationship paths are correctly inferred and joined.
    """
    async with join_db.session() as session:
        # Test 1: Direct model attribute in filter (Supported by Eden's involvement detection)
        # This should trigger select(Child).join(Parent).join(GrandParent).where(GrandParent.name == "GP1")
        children = await Child.query(session).filter(GrandParent.name == "GP1").all()
        assert len(children) == 1
        assert children[0].name == "C1"
        
@pytest.mark.asyncio
async def test_auto_join_performance(join_db):
    """
    AUDIT 2.2: Verify prefetch depth.
    """
    async with join_db.session() as session:
        # Use prefetch to see if deep paths work
        results = await GrandParent.query(session).prefetch("children.children").all()
        assert len(results) == 1
        assert len(results[0].children) == 1
        assert len(results[0].children[0].children) == 1
