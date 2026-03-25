import pytest
import uuid
from typing import List, Dict
from sqlalchemy.orm import Mapped
from eden.db import Model, f, Database
from eden.db import AccessControl, AllowOwner

# ── Audit Models ──────────────────────────────────────────────────────────

class AuditUser(Model):
    __tablename__ = "audit_users"
    username: Mapped[str] = f()

class SensitiveNote(Model, AccessControl):
    __tablename__ = "audit_notes"
    content: Mapped[str] = f()
    owner_id: Mapped[uuid.UUID] = f(foreign_key="audit_users.id")
    
    # RBAC: Only owner can read/write their own notes
    __rbac__ = {
        "read": AllowOwner(field="owner_id"),
        "write": AllowOwner(field="owner_id")
    }

# ── Audit Tests ───────────────────────────────────────────────────────────

@pytest.fixture
async def rbac_db():
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.connect()
    
    async with db.engine.begin() as conn:
        await conn.run_sync(Model.metadata.create_all)
        
    async with db.session() as session:
        u1 = await AuditUser.create(session, username="alice")
        u2 = await AuditUser.create(session, username="bob")
        
        await SensitiveNote.create(session, content="Alice's Secret", owner_id=u1.id)
        await SensitiveNote.create(session, content="Bob's Secret", owner_id=u2.id)
        await session.commit()
        
    yield db, u1, u2
    await db.disconnect()

@pytest.mark.asyncio
async def test_rbac_isolation_read(rbac_db):
    """
    AUDIT 2.3: RBAC Isolation.
    Verify that for_user() strictly filters records.
    """
    db, alice, bob = rbac_db
    async with db.session() as session:
        # 1. Query notes for Alice
        alice_notes = await SensitiveNote.query(session).for_user(alice).all()
        assert len(alice_notes) == 1
        assert alice_notes[0].content == "Alice's Secret"
        
        # 2. Query notes for Bob
        bob_notes = await SensitiveNote.query(session).for_user(bob).all()
        assert len(bob_notes) == 1
        assert bob_notes[0].content == "Bob's Secret"

@pytest.mark.asyncio
async def test_rbac_bypass_attempt(rbac_db):
    """
    AUDIT 2.3: Bypass probing.
    Attempt to bypass for_user() using .all() after calling for_user().
    """
    db, alice, bob = rbac_db
    async with db.session() as session:
        # Check if chaining .all() or other methods after for_user() retains the filter
        qs = SensitiveNote.query(session).for_user(alice)
        
        # Double check the statement has the where clause
        # The filter is owner_id == alice.id
        notes = await qs.all()
        assert len(notes) == 1
        
        # Attempt to "reset" the stmt by another call (QuerySet is immutable-ish via clone)
        all_notes = await SensitiveNote.query(session=session).bypass_rbac().all()
        assert len(all_notes) == 2 # Baseline
        
        # The for_user filter must be sticky on the cloned QuerySet
        notes_again = await qs.filter(content__icontains="Secret").all()
        assert len(notes_again) == 1
