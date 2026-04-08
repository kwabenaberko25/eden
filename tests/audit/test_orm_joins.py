import pytest
import asyncio
import uuid
from typing import List
from sqlalchemy.orm import Mapped
from eden.db import Model, f, Database

# ── Audit Models ──────────────────────────────────────────────────────────

class AuditGrandParent(Model):
    __tablename__ = "audit_grandparents"
    name: Mapped[str] = f()
    # Explicitly use Relationship to avoid SA 2.0 ArgumentError in tests
    children: Mapped[List["AuditParent"]] = f(back_populates="grandparent")

class AuditParent(Model):
    __tablename__ = "audit_parents"
    name: Mapped[str] = f()
    grandparent_id: Mapped[uuid.UUID] = f(foreign_key="audit_grandparents.id")
    grandparent: Mapped["AuditGrandParent"] = f(back_populates="children")
    children: Mapped[List["AuditChild"]] = f(back_populates="parent")

class AuditChild(Model):
    __tablename__ = "audit_children"
    name: Mapped[str] = f()
    parent_id: Mapped[uuid.UUID] = f(foreign_key="audit_parents.id")
    parent: Mapped["AuditParent"] = f(back_populates="children")

# ── Audit Tests ───────────────────────────────────────────────────────────

@pytest.fixture
async def join_db(tmp_path):
    db_path = tmp_path / "test_audit_joins.db"
    db = Database(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    await db.connect()
    
    async with db.engine.begin() as conn:
        try:
            await conn.run_sync(Model.metadata.create_all)
        except Exception as exc:
            if "already exists" in str(exc).lower():
                # SQLite may report existing indexes when metadata is reused across tests.
                pass
            else:
                raise
        
    async with db.session() as session:
        gp = await AuditGrandParent.create(session, name="GP1")
        p = await AuditParent.create(session, name="P1", grandparent_id=gp.id)
        c = await AuditChild.create(session, name="C1", parent_id=p.id)
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
        # This should trigger select(AuditChild).join(AuditParent).join(AuditGrandParent).where(AuditGrandParent.name == "GP1")
        children = await AuditChild.query(session).filter(AuditGrandParent.name == "GP1").all()
        assert len(children) == 1
        assert children[0].name == "C1"
        
@pytest.mark.asyncio
async def test_auto_join_performance(join_db):
    """
    AUDIT 2.2: Verify prefetch depth.
    """
    async with join_db.session() as session:
        # Use prefetch to see if deep paths work
        results = await AuditGrandParent.query(session).prefetch("children.children").all()
        assert len(results) == 1
        assert len(results[0].children) == 1
        assert len(results[0].children[0].children) == 1
