import pytest
from eden.auth.rbac import EdenRBAC
from eden.exceptions import Forbidden, Unauthorized
from eden.auth.decorators import require_permission
from eden.auth.models import BaseUser

class MockRequest:
    def __init__(self, user=None):
        self.user = user

class MockUser(BaseUser):
    def __init__(self, is_superuser=False, roles=None, permissions=None):
        self.is_superuser = is_superuser
        self.roles = roles or []
        self.permissions = permissions or []

def test_rbac_hierarchy():
    rbac = EdenRBAC()
    
    # admin inherits from manager, manager inherits from user
    rbac.add_role("user")
    rbac.add_role("manager", parents=["user"])
    rbac.add_role("admin", parents=["manager"])
    
    rbac.add_permission("user", "read:posts")
    rbac.add_permission("manager", "edit:posts")
    rbac.add_permission("admin", "delete:posts")
    
    # Test flat permissions
    assert "read:posts" in rbac.get_all_permissions("user")
    assert "edit:posts" not in rbac.get_all_permissions("user")
    
    # Test inherited permissions
    assert "read:posts" in rbac.get_all_permissions("manager")
    assert "edit:posts" in rbac.get_all_permissions("manager")
    assert "delete:posts" not in rbac.get_all_permissions("manager")
    
    # Test top-level inheritance
    assert "read:posts" in rbac.get_all_permissions("admin")
    assert "edit:posts" in rbac.get_all_permissions("admin")
    assert "delete:posts" in rbac.get_all_permissions("admin")

def test_has_permission():
    rbac = EdenRBAC()
    rbac.add_role("user")
    rbac.add_role("admin", parents=["user"])
    
    rbac.add_permission("user", "read")
    rbac.add_permission("admin", "write")
    
    assert rbac.has_permission(["user"], "read") is True
    assert rbac.has_permission(["user"], "write") is False
    assert rbac.has_permission(["admin"], "read") is True
    assert rbac.has_permission(["admin"], "write") is True

@pytest.mark.asyncio
async def test_require_permission_decorator(monkeypatch):
    import eden.auth.decorators
    
    # Mock get_current_user to return the request's user
    async def mock_get_current_user(request):
        return getattr(request, "user", None)
    
    monkeypatch.setattr(eden.auth.decorators, "get_current_user", mock_get_current_user)
    
    # Setup global RBAC
    from eden.auth.rbac import default_rbac
    default_rbac._hierarchy.clear()
    default_rbac._permissions.clear()
    
    default_rbac.add_role("user")
    default_rbac.add_role("editor", parents=["user"])
    default_rbac.add_permission("user", "read")
    default_rbac.add_permission("editor", "edit")
    
    @require_permission("edit")
    async def some_view(request):
        return "success"
        
    # 1. No user -> Unauthorized
    with pytest.raises(Unauthorized):
        await some_view(request=MockRequest())
        
    # 2. User with no roles/perms -> Forbidden
    with pytest.raises(Forbidden):
        await some_view(request=MockRequest(MockUser()))
        
    # 3. User with exact direct permission
    assert await some_view(request=MockRequest(MockUser(permissions=["edit"]))) == "success"
    
    # 4. User with exact role that grants permission
    assert await some_view(request=MockRequest(MockUser(roles=["editor"]))) == "success"
    
    # 5. User with parent role that doesn't grant permission
    with pytest.raises(Forbidden):
        await some_view(request=MockRequest(MockUser(roles=["user"])))
    
    # 6. Superuser bypasses checks
    assert await some_view(request=MockRequest(MockUser(is_superuser=True))) == "success"

