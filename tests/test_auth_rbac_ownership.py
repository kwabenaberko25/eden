import pytest
from sqlalchemy import String
from sqlalchemy.orm import Mapped
from eden.db import Model, Database, f
from eden.db.access import AccessControl, AllowOwner, AllowRoles

class SecretNote(Model, AccessControl):
    __tablename__ = "secret_notes"
    __rbac__ = {
        "read": AllowOwner("owner_id"),
        "delete": AllowRoles("admin")
    }
    
    content: Mapped[str] = f(max_length=255)
    owner_id: Mapped[int] = f()

class UserMock:
    def __init__(self, id, roles=None):
        self.id = id
        self.roles = roles or []

@pytest.mark.asyncio
async def test_rbac_allow_owner_isolation():
    """Verify that AllowOwner correctly isolates records per user."""
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.connect(create_tables=True)
    SecretNote._bind_db(db)
    
    async with db.session() as session:
        # Create notes for different users
        session.add_all([
            SecretNote(content="User 1 Note", owner_id=1),
            SecretNote(content="User 2 Note", owner_id=2),
        ])
        await session.commit()
    
    # Check for User 1
    user1 = UserMock(id=1)
    notes1 = await SecretNote.query().for_user(user1).all()
    assert len(notes1) == 1
    assert notes1[0].content == "User 1 Note"
    
    # Check for User 2
    user2 = UserMock(id=2)
    notes2 = await SecretNote.query().for_user(user2).all()
    assert len(notes2) == 1
    assert notes2[0].content == "User 2 Note"
    
    await db.disconnect()

@pytest.mark.asyncio
async def test_rbac_allow_roles():
    """Verify that AllowRoles allows/denies based on user roles."""
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.connect(create_tables=True)
    SecretNote._bind_db(db)
    
    user_regular = UserMock(id=1, roles=["user"])
    user_admin = UserMock(id=1, roles=["admin"])
    
    # Test 'delete' action which requires 'admin' role
    qs_reg = SecretNote.query().for_user(user_regular, action="delete")
    qs_admin = SecretNote.query().for_user(user_admin, action="delete")
    
    # For regular user, it should inject a false() filter (or equivalent)
    # We can check the statement
    assert "0 = 1" in str(qs_reg._stmt) or "false" in str(qs_reg._stmt).lower()
    
    # For admin, it should be the base select
    assert "0 = 1" not in str(qs_admin._stmt)
    
    await db.disconnect()
