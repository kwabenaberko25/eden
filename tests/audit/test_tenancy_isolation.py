import pytest
import uuid
from typing import List
from sqlalchemy.orm import Mapped
from eden.orm import Model, f, Database
from eden.tenancy.mixins import TenantMixin
from eden.tenancy.models import Tenant
from eden.tenancy.context import set_current_tenant

# ── Audit Models ──────────────────────────────────────────────────────────

class AuditProject(Model, TenantMixin):
    __tablename__ = "audit_projects"
    name: Mapped[str] = f()

# ── Audit Tests ───────────────────────────────────────────────────────────

@pytest.fixture
async def tenancy_db():
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.connect()
    
    async with db.engine.begin() as conn:
        await conn.run_sync(Model.metadata.create_all)
        
    async with db.session() as session:
        t1 = await Tenant.create(session, name="Tenant 1", slug="t1")
        t2 = await Tenant.create(session, name="Tenant 2", slug="t2")
        
        # Manually set tenant context to seed data
        token = set_current_tenant(t1)
        await AuditProject.create(session, name="P1 (T1)")
        from eden.tenancy.context import reset_current_tenant
        reset_current_tenant(token)
        
        token = set_current_tenant(t2)
        await AuditProject.create(session, name="P2 (T2)")
        reset_current_tenant(token)
        
        await session.commit()
        
    yield db, t1, t2
    await db.disconnect()

@pytest.mark.asyncio
async def test_tenant_isolation_basic(tenancy_db):
    """
    AUDIT 3.2: Tenant Data Leakage.
    Verify that row-level isolation works via context.
    """
    db, t1, t2 = tenancy_db
    async with db.session() as session:
        # 1. Switch context to T1
        token = set_current_tenant(t1)
        try:
            projects = await AuditProject.query(session).all()
            assert len(projects) == 1
            assert projects[0].name == "P1 (T1)"
            assert projects[0].tenant_id == t1.id
        finally:
            from eden.tenancy.context import reset_current_tenant
            reset_current_tenant(token)

        # 2. Switch context to T2
        token = set_current_tenant(t2)
        try:
            projects = await AuditProject.query(session).all()
            assert len(projects) == 1
            assert projects[0].name == "P2 (T2)"
            assert projects[0].tenant_id == t2.id
        finally:
            from eden.tenancy.context import reset_current_tenant
            reset_current_tenant(token)

@pytest.mark.asyncio
async def test_tenant_leakage_on_missing_context(tenancy_db):
    """
    AUDIT 3.2: Fail-Secure behavior.
    Verify that if NO tenant is set in context, it returns NO records (rather than all).
    """
    db, t1, t2 = tenancy_db
    async with db.session() as session:
        # NO set_current_tenant called
        projects = await AuditProject.query(session).all()
        
        # Finding: If this returns 2, it's a critical leakage on missing context.
        # TenantMixin._apply_tenant_filter uses stmt.where(false()) if no id found.
        assert len(projects) == 0

@pytest.mark.asyncio
async def test_tenant_bypass_manual_where(tenancy_db):
    """
    AUDIT 3.2: Verify that for_tenant() or manual filters don't bypass isolation.
    Actually, manual filters should be ANDed.
    """
    db, t1, t2 = tenancy_db
    async with db.session() as session:
        token = set_current_tenant(t1)
        try:
            # Attempt to query specifically for T2's ID while in T1 context
            # SQL: WHERE tenant_id = T1 AND tenant_id = T2
            projects = await AuditProject.query(session).filter(tenant_id=t2.id).all()
            assert len(projects) == 0
        finally:
            from eden.tenancy.context import reset_current_tenant
            reset_current_tenant(token)
