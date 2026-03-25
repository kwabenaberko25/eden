import pytest
import uuid
from unittest.mock import MagicMock
from eden.auth.models import User, Role, Permission

@pytest.mark.asyncio
async def test_relational_rbac_hierarchy_resolution():
    """Test that permissions and roles are correctly resolved through the hierarchy."""
    
    # Setup IDs
    u_id = uuid.uuid4()
    r_user_id = uuid.uuid4()
    r_manager_id = uuid.uuid4()
    r_admin_id = uuid.uuid4()
    
    p_read_id = uuid.uuid4()
    p_write_id = uuid.uuid4()
    p_delete_id = uuid.uuid4()

    # 1. Create Permissions
    p_read = Permission(id=p_read_id, name="read:posts")
    p_write = Permission(id=p_write_id, name="write:posts")
    p_delete = Permission(id=p_delete_id, name="delete:posts")
    
    # 2. Create Roles with Hierarchy
    # user role
    role_user = Role(id=r_user_id, name="user")
    role_user.permissions = [p_read]
    
    # manager role (inherits from user)
    role_manager = Role(id=r_manager_id, name="manager")
    role_manager.permissions = [p_write]
    role_manager.parents = [role_user]
    
    # admin role (inherits from manager)
    role_admin = Role(id=r_admin_id, name="admin")
    role_admin.permissions = [p_delete]
    role_admin.parents = [role_manager]
    
    # 3. Create User and assign Admin role
    user = User(id=u_id, email="test@example.com")
    user.roles = [role_admin]
    
    # 4. Verify Role Name Resolution
    role_names = await user.get_all_role_names()
    assert "admin" in role_names
    assert "manager" in role_names
    assert "user" in role_names
    assert len(role_names) == 3
    
    # 5. Verify Permission Resolution
    all_perms = await user.get_all_permissions()
    assert "read:posts" in all_perms
    assert "write:posts" in all_perms
    assert "delete:posts" in all_perms
    assert len(all_perms) == 3
    
    # 6. Verify has_permission method
    assert await user.has_permission("read:posts") is True
    assert await user.has_permission("delete:posts") is True
    assert await user.has_permission("other:perm") is False

@pytest.mark.asyncio
async def test_rbac_circular_dependency_handling():
    """Test that circular dependencies in roles do not cause infinite recursion."""
    
    r1_id = uuid.uuid4()
    r2_id = uuid.uuid4()
    
    role1 = Role(id=r1_id, name="r1")
    role2 = Role(id=r2_id, name="r2")
    
    # Circular: r1 -> r2 -> r1
    role1.parents = [role2]
    role2.parents = [role1]
    
    user = User(id=uuid.uuid4(), email="circular@example.com")
    user.roles = [role1]
    
    # This should not hang
    names = await user.get_all_role_names()
    assert "r1" in names
    assert "r2" in names
    assert len(names) == 2

@pytest.mark.asyncio
async def test_rbac_legacy_fallback():
    """Test that JSON-based legacy roles/permissions still work alongside relational ones."""
    
    # Relational stuff
    p_rel = Permission(id=uuid.uuid4(), name="relational:perm")
    role_rel = Role(id=uuid.uuid4(), name="relational_role")
    role_rel.permissions = [p_rel]
    
    # User with both
    user = User(
        id=uuid.uuid4(), 
        email="hybrid@example.com",
        roles_json=["legacy_role"],
        permissions_json=["legacy:perm"]
    )
    user.roles = [role_rel]
    
    # Check permissions
    perms = await user.get_all_permissions()
    assert "relational:perm" in perms
    assert "legacy:perm" in perms
    
    # Check roles
    roles = await user.get_all_role_names()
    assert "relational_role" in roles
    assert "legacy_role" in roles

@pytest.mark.asyncio
async def test_superuser_bypass():
    """Test that superusers bypass all RBAC checks."""
    
    user = User(id=uuid.uuid4(), email="super@example.com", is_superuser=True)
    
    assert await user.has_permission("any:thing") is True
    assert await user.has_role("any:role") is True

@pytest.mark.asyncio
async def test_allow_roles_rule_with_hierarchy():
    """Test that the AllowRoles rule correctly resolves hierarchical roles for RLS."""
    from eden.db.access import AllowRoles
    
    # Setup Roles
    role_user = Role(id=uuid.uuid4(), name="user")
    role_admin = Role(id=uuid.uuid4(), name="admin")
    role_admin.parents = [role_user]
    
    user = User(id=uuid.uuid4(), email="admin@example.com")
    user.roles = [role_admin]
    
    # 1. Rule requires 'user' role
    rule_user = AllowRoles("user")
    # Admin should pass because they inherit from user
    assert rule_user.resolve(None, user) is True
    
    # 2. Rule requires 'admin' role
    rule_admin = AllowRoles("admin")
    assert rule_admin.resolve(None, user) is True
    
    # 3. Rule requires 'manager' (not in hierarchy)
    rule_manager = AllowRoles("manager")
    assert rule_manager.resolve(None, user) is False
