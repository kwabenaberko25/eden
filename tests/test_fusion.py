import uuid
from sqlalchemy.orm import Mapped
from eden.db import Model, f, QuerySet
from eden.context import set_user, reset_user
from eden.db import AccessControl
from sqlalchemy import Column, ForeignKey, Uuid, func

class TenantModel(Model, AccessControl):
    __abstract__ = True
    tenant_id: Mapped[uuid.UUID] = f(org_id=True, required=True)

    @classmethod
    def get_security_filters(cls, user, action):
        if not user: return False
        # Automatic isolation: only see records for the user's active organization
        return cls.tenant_id == user.active_org_id

class FusionProject(TenantModel):
    name: Mapped[str] = f(max_length=100)

class FusionTask(TenantModel):
    title: Mapped[str] = f(max_length=100)
    project_id: Mapped[uuid.UUID] = f(foreign_key="fusion_projects.id")

import pytest

@pytest.fixture(autouse=True)
async def setup_db(db):
    async with db.engine.begin() as conn:
        # We need to drop first to avoid conflicts if previously failed
        await conn.run_sync(Model.metadata.drop_all)
        await conn.run_sync(Model.metadata.create_all)
    yield
    async with db.engine.begin() as conn:
        await conn.run_sync(Model.metadata.drop_all)

class MockUser:
    def __init__(self, org_id):
        self.active_org_id = org_id

from eden.context import set_user, reset_user

@pytest.mark.asyncio
async def test_multi_tenancy_auto_isolation():
    org_a = uuid.uuid4()
    org_b = uuid.uuid4()
    
    # Simulate Org A user context
    user_a = MockUser(org_a)
    token = set_user(user_a)
    try:
        await FusionProject.create(name="Project A", tenant_id=org_a)
    finally:
        reset_user(token)
        
    # Simulate Org B user context
    user_b = MockUser(org_b)
    token = set_user(user_b)
    try:
        await FusionProject.create(name="Project B", tenant_id=org_b)
    finally:
        reset_user(token)
        
    # Verify Isolation
    token = set_user(user_a)
    try:
        projects = await FusionProject.query().for_user(user_a).all()
        assert len(projects) == 1
        assert projects[0].name == "Project A"
    finally:
        reset_user(token)
        
    token = set_user(user_b)
    try:
        projects = await FusionProject.query().for_user(user_b).all()
        assert len(projects) == 1
        assert projects[0].name == "Project B"
    finally:
        reset_user(token)

@pytest.mark.asyncio
async def test_fusion_rbac_hooks():
    # Test if hooks can intercept and prevent access
    org_a = uuid.uuid4()
    user_a = MockUser(org_a)
    
    token = set_user(user_a)
    try:
        p = await FusionProject.create(name="Secret", tenant_id=org_a)
    finally:
        reset_user(token)
    
    # Non-tenant user should see nothing
    user_none = MockUser(uuid.uuid4())
    token = set_user(user_none)
    try:
        projects = await FusionProject.query().for_user(user_none).all()
        assert len(projects) == 0
    finally:
        reset_user(token)
        
@pytest.mark.asyncio
async def test_orm_context_fusion_creation():
    # Test if we can auto-populate tenant_id from context (if we implement it in base.py)
    # Actually, current base.py might not do this yet, let's verify.
    pass
