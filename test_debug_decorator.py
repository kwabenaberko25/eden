import pytest
from unittest.mock import Mock

@pytest.mark.asyncio
async def test_debug_require_permission():
    """Debug test for require_permission decorator - MATCHES THE ACTUAL TEST."""
    from eden.auth import require_permission
    from eden.exceptions import PermissionDenied

    # Monkey-patch the decorator to add debug output
    import eden.auth.decorators
    original_require_permission = eden.auth.decorators.require_permission
    
    def debug_require_permission(permission: str):
        def decorator(func):
            import functools
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                print(f"[DECORATOR] Called with args={args}, kwargs={kwargs}")
                request = kwargs.get("request")
                print(f"[DECORATOR] request from kwargs: {request}")
                if not request and args:
                    request = args[0]
                    print(f"[DECORATOR] request from args[0]: {request}")
                
                if not request:
                    raise RuntimeError("Request object not found in view arguments.")
                
                user = getattr(request, "user", None)
                print(f"[DECORATOR] user: {user}")
                if not user:
                    from eden.exceptions import Unauthorized
                    raise Unauthorized(detail="Login required.")
                
                if getattr(user, "is_superuser", False):
                    print(f"[DECORATOR] User is superuser - allowing")
                    return await func(*args, **kwargs)
                
                # Check direct permissions
                user_permissions = getattr(user, "permissions", [])
                print(f"[DECORATOR] user_permissions: {user_permissions}")
                print(f"[DECORATOR] permission in user_permissions: {permission in user_permissions}")
                if permission in user_permissions:
                    print(f"[DECORATOR] Found direct permission - allowing")
                    return await func(*args, **kwargs)
                
                # Check RBAC hierarchy
                print(f"[DECORATOR] Checking RBAC...")
                try:
                    from eden.auth.rbac import default_rbac
                    user_roles = getattr(user, "roles", [])
                    print(f"[DECORATOR] user_roles: {user_roles} (type: {type(user_roles)})")
                    rbac_result = default_rbac.has_permission(user_roles, permission)
                    print(f"[DECORATOR] RBAC result: {rbac_result}")
                    if rbac_result:
                        print(f"[DECORATOR] RBAC check passed - allowing")
                        return await func(*args, **kwargs)
                except Exception as e:
                    print(f"[DECORATOR] RBAC check error: {type(e).__name__}: {e}")
                    raise
                
                print(f"[DECORATOR] Denying access")
                raise PermissionDenied(detail=f"Missing required permission: {permission}")
            
            return wrapper
        return decorator

    # Replace for testing
    eden.auth.decorators.require_permission = debug_require_permission

    @debug_require_permission("admin_access")
    async def admin_only(request):
        return {"message": "admin"}

    # Create mock request with user - with explicit attributes
    request = Mock()
    request.user = Mock()
    request.user.permissions = ["admin_access"]
    request.user.is_superuser = False  # MUST SET THIS!
    request.user.roles = []  # And this!

    # Should succeed
    print("=" * 50)
    print("Test 1: User WITH permission should succeed")
    result = await admin_only(request)
    print(f"✓ Result: {result}")

    # User without permission should fail
    print("\n" + "=" * 50)
    print("Test 2: User WITHOUT permission should raise")
    request.user.permissions = []
    request.user.is_superuser = False
    request.user.roles = []
    
    try:
        result = await admin_only(request)
        print(f"✗ PROBLEM: Decorator did not raise - returned: {result}")
    except PermissionDenied as e:
        print(f"✓ Correctly raised PermissionDenied: {e}")
    except Exception as e:
        print(f"✗ Raised wrong exception: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_debug_require_permission())




