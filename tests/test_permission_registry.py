import pytest
from eden.auth.rbac import PermissionRegistry
from eden.auth.access import check_permission
from eden.auth.base import BaseUser
import asyncio

class DummyUser(BaseUser):
    def __init__(self, id=1, superuser=False):
        self.id = id
        self.is_superuser = superuser
    
    async def has_permission(self, permission: str) -> bool:
        # Dummy backend
        return permission == "post:read"

@pytest.mark.asyncio
async def test_permission_registry_fast_path():
    registry = PermissionRegistry()
    
    async def my_policy(user, resource):
        return True
    
    # Register the local policy
    registry.register("post:edit", my_policy)
    
    user = DummyUser()
    
    # Should evaluate internal declarative registry
    res = await registry.evaluate("post:edit", user)
    assert res is True
    
    # Should return None if no local policy
    res2 = await registry.evaluate("missing", user)
    assert res2 is None
