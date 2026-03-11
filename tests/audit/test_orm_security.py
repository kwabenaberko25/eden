import pytest
import uuid
from sqlalchemy.orm import Mapped
from eden.db import Model, f, Database, Q

# ── Audit Models ──────────────────────────────────────────────────────────

class SecretData(Model):
    __tablename__ = "secrets"
    key: Mapped[str] = f()
    value: Mapped[str] = f()

class UserAccount(Model):
    __tablename__ = "user_accounts"
    username: Mapped[str] = f()
    is_admin: Mapped[bool] = f(default=False)

# ── Audit Tests ───────────────────────────────────────────────────────────

@pytest.fixture
async def audit_db():
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.connect()
    
    async with db.engine.begin() as conn:
        await conn.run_sync(Model.metadata.create_all)
        
    async with db.session() as session:
        # Seed sensitive data
        await SecretData.create(session, key="FLAG", value="EDEN_AUDIT_SUCCESS")
        await UserAccount.create(session, username="admin", is_admin=True)
        await UserAccount.create(session, username="victim", is_admin=False)
        await session.commit()
        
    yield db
    await db.disconnect()

@pytest.mark.asyncio
async def test_orm_lookup_sql_injection(audit_db):
    """
    AUDIT 2.1: SQL Injection Probing.
    Attempt to inject malicious strings through Django-style lookups.
    """
    async with audit_db.session() as session:
        # Payload 1: Attempt to break out of string quote and execute UNION or extra statement
        # SQLite: 'victim') OR 1=1 --
        malicious_username = "victim') OR 1=1 --"
        
        # Test 1: Exact lookup
        users = await UserAccount.filter(session, username=malicious_username).all()
        # SUCCESS: Should find NO users because SQLAlchemy uses bind parameters
        assert len(users) == 0, "SQL Injection vulnerability found in exact lookup!"

        # Test 2: Contains lookup (LIKE)
        # Payload: %' OR '1'='1
        malicious_search = "%' OR '1'='1"
        users = await UserAccount.filter(session, username__icontains=malicious_search).all()
        # SUCCESS: Should find NO users because the % and ' are correctly escaped/bound
        assert len(users) == 0, "SQL Injection vulnerability found in icontains lookup!"

        # Test 3: Attempting to comment out the rest of the query
        # username='foo' OR is_admin=1 --
        injection_payload = "foo' OR is_admin=1 --"
        users = await UserAccount.filter(session, username=injection_payload).all()
        assert len(users) == 0, "SQL Injection via comment injection!"

@pytest.mark.asyncio
async def test_orm_q_object_injection(audit_db):
    """
    AUDIT 2.2: Q Object Probing.
    """
    async with audit_db.session() as session:
        # Payload: Q(username="' OR '1'='1")
        malicious_q = Q(username="' OR '1'='1") | Q(is_admin=True)
        users = await UserAccount.filter(session, malicious_q).all()
        
        # Should only find the admin user seeded in fixture
        assert len(users) == 1
        assert users[0].username == "admin"
        
        # Verify that the malicious part didn't match everyone
        all_count = await UserAccount.count(session)
        assert len(users) < all_count

@pytest.mark.asyncio
async def test_orm_raw_expression_bypass(audit_db):
    """
    AUDIT 2.3: Verifying that we don't accidentally allow raw SQL strings in filter()
    """
    async with audit_db.session() as session:
        # Eden filter should raise ValueError or bind the string if it's not a known field
        # and doesn't support raw string expressions directly.
        
        with pytest.raises(ValueError) as exc:
            # Attempt to use a non-existent field as a vector
            await UserAccount.filter(session, **{"username=1; --": "dummy"}).all()
        assert "has no column" in str(exc.value)
