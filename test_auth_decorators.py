#!/usr/bin/env python
"""
Quick test of auth decorators
"""
import asyncio
from eden.auth.decorators import (
    login_required,
    roles_required,
    permissions_required,
    require_permission,
    is_authorized,
    bind_user_principal,
)

async def test_decorator_imports():
    """Test that all decorators can be imported and applied."""
    
    # Test 1: login_required decorator
    @login_required
    async def protected_view(request):
        return {"message": "You are logged in"}
    
    assert callable(protected_view), "login_required should return a callable"
    print("✓ login_required decorator works")
    
    # Test 2: roles_required decorator
    @roles_required(["admin", "moderator"])
    async def admin_view(request):
        return {"message": "Admin area"}
    
    assert callable(admin_view), "roles_required should return a callable"
    print("✓ roles_required decorator works")
    
    # Test 3: permissions_required decorator
    @permissions_required(["view_reports", "edit_reports"])
    async def reports_view(request):
        return {"message": "Reports"}
    
    assert callable(reports_view), "permissions_required should return a callable"
    print("✓ permissions_required decorator works")
    
    # Test 4: require_permission decorator
    @require_permission("delete_user")
    async def delete_user_view(request):
        return {"message": "User deleted"}
    
    assert callable(delete_user_view), "require_permission should return a callable"
    print("✓ require_permission decorator works")
    
    # Test 5: is_authorized decorator
    @is_authorized
    async def authorized_view(request):
        return {"message": "You are authorized"}
    
    assert callable(authorized_view), "is_authorized should return a callable"
    print("✓ is_authorized decorator works")
    
    # Test 6: bind_user_principal decorator
    @bind_user_principal
    async def principal_view(request):
        return {"message": "User principal bound"}
    
    assert callable(principal_view), "bind_user_principal should return a callable"
    print("✓ bind_user_principal decorator works")
    
    print("\n✅ All auth decorators imported and applied successfully!")

if __name__ == "__main__":
    asyncio.run(test_decorator_imports())
